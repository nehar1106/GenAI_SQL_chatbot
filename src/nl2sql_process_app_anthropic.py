import boto3
import json
import psycopg2
import os
from typing import List, Dict, Any
from botocore.exceptions import ClientError
import re

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'ACCESSKEYEXAMPLE')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
AWS_SESSION_TOKEN = os.environ.get('AWS_SESSION_TOKEN', '')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-2')

if AWS_ACCESS_KEY_ID == 'ACCESSKEYEXAMPLE':
    print("ERROR: AWS credentials not configured")
    exit(1)

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN,  # Add this line
    region_name=AWS_REGION
)

def test_aws_connection():
    try:
        s3_client = session.client('s3')
        response = s3_client.list_buckets()
        print(f"AWS connection OK - found {len(response['Buckets'])} buckets")
        return True
    except Exception as e:
        print(f"AWS connection failed: {str(e)}")
        return False


def _get_schema_context(question: str) -> dict:
    try:
        client = session.client('bedrock-agent-runtime')
        kb_id = os.environ.get('KNOWLEDGE_BASE_ID', 'BVXKGDUMDF')

        response = client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": question},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": 3}
            }
        )
        
        schema_context = {"tables": [], "relationships": [], "sample_queries": []}
        for chunk in response['retrievalResults']:
            content = chunk['content']['text']
            if content:
                schema_context['tables'].append(content)
        return schema_context
    except Exception as e:
        print(f"Schema retrieval failed: {str(e)}")
        return {"tables": []}

def _format_schema_context(schema_context: dict) -> str:
    context = []
    if schema_context['tables']:
        context.append("Database Schema:")
        for table in schema_context['tables']:
            if isinstance(table, str):
                context.append(f"\n{table}")
            else:
                context.append(f"\nTable: {table['name']}")
                for column in table['columns']:
                    context.append(f"- {column['name']}: {column['type']}")
    if schema_context['relationships']:
        context.append("\nRelationships:")
        for rel in schema_context['relationships']:
            context.append(f"- {rel['description']}")
    return '\n'.join(context)


def format_results(data: List[tuple], columns: List[str]) -> str:
    if not data:
        return "No results found."
    
    rows = []
    for row in data:
        row_str = '|'.join(f"{str(item):<30}" for item in row)
        rows.append(row_str)

    header = '|'.join(f"{col:<30}" for col in columns)
    separator = '|'.join('_'*30 for _ in columns)

    return "\n".join([header, separator] + rows)

def format_tab_results(data: List[tuple], columns: List[str]) -> str:
    """Format SQL results in tabular format with pipe separators"""
    if not data:
        return "No results found."
    header = " | ".join(columns)

    separator = "-" * len(header)

    rows = []
    for row in data:
        formatted_row = " | ".join(str(cell) if cell is not None else "NULL" for cell in row)
        rows.append(formatted_row)
    
    return "\n".join([header, separator] + rows)

def execute_sql_on_aurora(sql_query: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute(sql_query)
        
        if sql_query.strip().upper().startswith('SELECT'):
            results = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return {
                'success': True,
                'data': results,
                'columns': columns,
                'row_count': len(results),
                'query': sql_query
            }
        else:
            conn.commit()
            return {
                'success': True,
                'affected_rows': cur.rowcount,
                'query': sql_query,
                'message': f"Query executed. {cur.rowcount} rows affected."
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'query': sql_query
        }
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def generate_sql_with_anthropic(user_question: str, error_context: str = None) -> str:
    schema_context = _get_schema_context(user_question)
    schema = _format_schema_context(schema_context)
    
    if error_context:
        prompt = f"""Fix this SQL query:

{schema}

Question: {user_question}
Error: {error_context}

Return only the corrected PostgreSQL query:"""
    else:
        prompt = f"""Generate PostgreSQL query:

{schema}

Question: {user_question}

Return only the SQL query:"""
    
    try:
        bedrock = session.client('bedrock-runtime')
        
        resp = bedrock.invoke_model(
            modelId='us.anthropic.claude-3-5-haiku-20241022-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 1000,
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )
        
        result = json.loads(resp['body'].read())
        sql = result['content'][0]['text'].strip()
        
        if '```sql' in sql:
            sql = sql.split('```sql')[1].split('```')[0].strip()
        elif '```' in sql:
            sql = sql.split('```')[1].strip()
        
        return sql
        
    except Exception as e:
        print(f"SQL generation failed: {str(e)}")
        return None

def query_database_with_nl(user_question: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
    max_retries = 2
    last_error = None
    sql = None
    
    for attempt in range(max_retries):
        if attempt == 0:
            sql = generate_sql_with_anthropic(user_question)
        else:
            sql = generate_sql_with_anthropic(user_question, last_error)
        
        if not sql:
            continue
            
        result = execute_sql_on_aurora(sql, db_config)
        
        if result['success']:
            return {
                'question': user_question,
                'generated_sql': sql,
                'execution_result': result,
                'success': True,
                'attempts': attempt + 1
            }
        
        last_error = result['error']
    
    return {
        'question': user_question,
        'generated_sql': sql,
        'execution_result': result if 'result' in locals() else None,
        'success': False,
        'attempts': max_retries,
        'final_error': last_error
    }

def lambda_handler(event, context):
    try:
        user_query = event.get('user_query')
        if not user_query:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing user_query parameter',
                    'success': False
                })
            }

        secrets_client = session.client('secretsmanager', region_name='us-east-2')
        
        try:
            secret_response = secrets_client.get_secret_value(SecretId='dev/sb2/appdb2')
        except ClientError as e:
            raise e

        secret = json.loads(secret_response['SecretString'])
        
        db_config = {
            'host': secret['host'],
            'database': secret['username'],
            'user': secret['username'],
            'password': secret['password'],
            'port': '5432'
        }

        required_params = ['host', 'database', 'user', 'password']
        missing = [p for p in required_params if not db_config[p]]
        if missing:
            return {
                'statusCode': 501,
                'body': json.dumps({
                    'error': f'Missing DB config: {missing}',
                    'success': False
                })
            }
        
        result = query_database_with_nl(user_query, db_config)
        
        if result['success'] and result['execution_result'].get('data'):
            formatted_data = format_results(
                result['execution_result']['data'], 
                result['execution_result']['columns']
            )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'question': result['question'],
                'generated_sql': result['generated_sql'],
                'success': result['success'],
                'attempts': result['attempts'],
                'data': result['execution_result'].get('data', []) if result['success'] else None,
                'cols': result['execution_result'].get('columns', []) if result['success'] else None,
                'row_count': result['execution_result'].get('row_count', 0) if result['success'] else 0,
                'error': result.get('final_error') if not result['success'] else None
            }, default=str)
        }
        
    except Exception as e:
        return {
            'statusCode': 502,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}',
                'success': False
            })
        }

if __name__ == "__main__":
    if not test_aws_connection():
        exit(1)
    
    event = {'user_query': 'give me all the customers'}
    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))

