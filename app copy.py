import streamlit as st
from openai import OpenAI
from qdrant_client import QdrantClient
from typing import List
import pandas as pd
from dotenv import load_dotenv
import os
load_dotenv()


st.set_page_config(layout="wide")

# Sidebar: Input fields for OpenAI API Key and Qdrant host and port
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=os.getenv('OPENAI_KEY'))  # Secure input for API Key
qdrant_host = st.sidebar.text_input("Qdrant Host", os.getenv('QDRANT_HOST'))  # Default host
qdrant_port = st.sidebar.number_input("Qdrant Port", min_value=1, max_value=65535, value=int(os.getenv('QDRANT_PORT')))  # Default port

# Main content layout with a single column
st.title("Qdrant Query App")

# User input for the query

# User input for the limit
user_query = st.text_input("Type your question here:")

# Qdrant client setup based on user input
def get_embedding(query: str, model: str = "text-embedding-ada-002") -> List[float]:
    client = OpenAI(api_key=api_key)

    response = client.embeddings.create(
        input=query,
        model=model
    )
    return response.data[0].embedding

# Function to query Qdrant and fetch results
def query_qdrant(user_query: str, limit: int, collection_name: str):
    try:
        # Step 1: Convert user query to vector
        embedding_vector = get_embedding(user_query)

        # Step 2: Query Qdrant with the embedding vector
        client = QdrantClient(
            host=qdrant_host, 
            port=qdrant_port,
            api_key="Y3NMMGK3Okzt7rzho88jhmzPZl5MhmAtwFbLG4OJPGRtNV7pH8sOlVNtveGcejEl"

            )  # Use the user-defined host and port
        hits = client.search(
            collection_name=collection_name,
            query_vector=embedding_vector,
            limit=limit  # Use the dynamic limit
        )

        # Step 3: Extract relevant fields (page_content and source) from the search results
        results = []
        for hit in hits:
            payload = hit.payload
            result = {
                "source": payload.get("metadata", {}).get("source", "No source found"),
                "page_content": payload.get("page_content", "No content found")
            }
            results.append(result)
        return results
    except Exception as e:
        return [{"error": str(e)}]

# Function to list available collections
def get_collections():
    try:
        client = QdrantClient(
            host=qdrant_host, 
            port=qdrant_port,
            api_key="Y3NMMGK3Okzt7rzho88jhmzPZl5MhmAtwFbLG4OJPGRtNV7pH8sOlVNtveGcejEl"
            )
        collections_response = client.get_collections()
        # Access the collections attribute to get the actual list of collections
        collections = collections_response.collections
        return collections
    except Exception as e:
        return [{"error": str(e)}]

col1, col2 = st.columns(2)

with col1:
    # User input for the limit (number of top closest records to fetch)
    limit = st.number_input("Number of top closest records to fetch:", min_value=1, max_value=100, value=10)

with col2:
    # Get available collections and display them in a selectbox
    collections = get_collections()
    print(collections)
    collection_names = [c['name'] for c in collections]
    selected_collection = st.selectbox("Select a collection", collection_names)


# Submit button
if st.button("Submit"):
    if user_query and selected_collection:
        st.info("Processing your query...")
        # Fetch results with the user-defined limit and selected collection
        results = query_qdrant(user_query, limit, selected_collection)

        # Display results in a table format
        if results:
            df = pd.DataFrame(results)
            st.table(df)  # Display the table
        else:
            st.warning("No results found.")
    else:
        st.error("Please enter a query and select a collection.")
