import streamlit as st
import json
from nl2sql_process_app_anthropic import lambda_handler, format_results

st.set_page_config(
    page_title="Gen AI Chatbot - SQL Query Assistant",
    page_icon="💬",
    layout="wide"
)

# -- Set title
st.title("Gen AI Chatbot - SQL Query Assistant")
st.markdown("Converts natural language to SQL queries and displays the results on this page")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Enter your question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            try:
                event = {"user_query": prompt}
                result = lambda_handler(event, None)
                
                if result['statusCode'] == 200:
                    body = json.loads(result['body'])
                    print(f"Response keys: {list(body.keys())}")
                    print(f"Response body: {body}")
                    
                    if body['success']:
                        print("Query executed successfully")
                        response = f"**SQL Query:**\n```sql\n{body['generated_sql']}\n```\n\n"
                        print(f"Generated response: {response}")

                        # -- If query returned data, format in tabular format for displaying on Chat page
                        if body['data'] and body['row_count'] > 0:
                            print(f"Processing {body['row_count']} rows of data")
                            table_data = format_results(body['data'], body['cols'])
                            print(f"Formatted table data: {table_data}")
                            response += f"**Results ({body['row_count']} rows):**\n```\n{table_data}\n```"
                        else:
                            response += "**Results:** No data found."
                    else:
                        response = f"**Error:** {body.get('error', 'Query failed')}"
                else:
                    response = f"**Error:** Request failed (status {result['statusCode']})"
                
            except Exception as e:
                response = f"**Error:** {str(e)}"
        
        st.markdown(response)
        print(f"Final response sent to UI: {response}")
    
    st.session_state.messages.append({"role": "assistant", "content": response})

with st.sidebar:
    st.header("About")
    st.markdown("""
    Converts natural language to SQL queries and executes them.
    
    **Examples:**
    - "Show all customers"
    - "Give me all customer details who are from Africa"
    - "Give me all customer details who are from africa including their nation and region information"
    - "Show me list of nations"

    """)
    
    if st.button("Clear History"):
        st.session_state.messages = []
        st.rerun()
