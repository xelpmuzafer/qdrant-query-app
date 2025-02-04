import streamlit as st
from openai import OpenAI
from qdrant_client import QdrantClient
from typing import List
import pandas as pd
from dotenv import load_dotenv
import os
from qdrant_client.models import Filter, FieldCondition, MatchValue


load_dotenv()

st.set_page_config(layout="wide")



# # Sidebar: Input fields for OpenAI API Key and Qdrant configuration
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=os.getenv('OPENAI_KEY'))  # Secure input for API Key
qdrant_host = st.sidebar.text_input("Qdrant Host", os.getenv('QDRANT_HOST'))  # Default host
qdrant_port = st.sidebar.number_input("Qdrant Port", min_value=1, max_value=65535, value=int(os.getenv('QDRANT_PORT')) if os.getenv('QDRANT_PORT') else None )  # Default port
qdrant_api_key = st.sidebar.text_input("Qdrant API Key (Optional)", type="password")  # Optional API Key

# Main content layout with a single column



client = QdrantClient(
            host=qdrant_host,
            port=qdrant_port,
            api_key=qdrant_api_key if qdrant_api_key else None  # Use API Key if provided
        )

tab1 , tab2 = st.tabs(["Similarity search", "Filter by source"])

# Function to get embedding
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
        # Convert user query to vector
        embedding_vector = get_embedding(user_query)

        # Setup QdrantClient
        
        
        # Search in Qdrant
        hits = client.search(
            collection_name=collection_name,
            query_vector=embedding_vector,
            limit=limit  # Use the dynamic limit
        )

        # Extract relevant fields
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
    if not qdrant_host or not qdrant_port:
        return []
    try:
        client = QdrantClient(
            host=qdrant_host,
            port=qdrant_port,
            api_key=qdrant_api_key if qdrant_api_key else None  # Use API Key if provided
        )
        collections_response = client.get_collections()
        # Access the collections attribute to get the actual list of collections
        collections = collections_response.collections
        return collections
    except Exception as e:
        return [{"error": str(e)}]

def get_qdrant_docs(collection_name, source_url):

    # Define the collection name

    # Define the filter for metadata
    metadata_filter = Filter(
        must=[
            FieldCondition(
                key="metadata.source",  # Replace with your metadata field
                match=MatchValue(value=source_url)  # Replace with the value to filter by
            )
        ]
    )

    # Scroll through the collection with the filter
    response = client.scroll(
        collection_name=collection_name,
        scroll_filter=metadata_filter,
        limit=100,  # Adjust the limit as needed
        with_payload=True,  # Include the payload (metadata) in the response
        with_vectors=False  # Exclude vectors if not needed
    )

    return [point.payload for point in response[0]]



collections = get_collections()

with tab1:
    # User input for the query
    user_query = st.text_input("Type your question here:")

    col1, col2 = st.columns(2)

    with col1:
        # User input for the limit (number of top closest records to fetch)
        limit = st.number_input("Number of top closest records to fetch:", min_value=1, max_value=100, value=10)

    with col2:
        # Get available collections and display them in a selectbox
        if collections and isinstance(collections, list) and "error" in collections[0]:
            st.error("Error fetching collections: " + collections[0]["error"])
            collection_names = []
        else:
            collection_names = [c.name for c in collections]
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


with tab2:
    if collections and isinstance(collections, list) and "error" in collections[0]:
        st.error("Error fetching collections: " + collections[0]["error"])
        collection_names = []
    else:
        collection_names = [c.name for c in collections]
        selected_collection = st.selectbox("Select a collection", collection_names, key="2")
    user_query = st.text_input("Enter source url:")
    if st.button("Submit", key="4"):
        points  = get_qdrant_docs(selected_collection, user_query)
        formatted = []
        for x in points:
            formatted.append({
               "source" : x['metadata']['source'],
               "page_content" : x['page_content']
            })
        st.table(pd.DataFrame(formatted))

