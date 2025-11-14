import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import ast
import sys
import os

def main():
    # Check if filename is provided
    if len(sys.argv) != 2:
        print("Usage: python pca_analysis.py <input_csv_file>")
        print("Example: python pca_analysis.py gemini_embeddings.csv")
        sys.exit(1)
    
    input_filename = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(input_filename):
        print(f"Error: File '{input_filename}' not found.")
        sys.exit(1)
    
    # Generate output filename
    base_name = os.path.splitext(input_filename)[0]
    output_filename = f"{base_name}_pca.csv"
    analysis_filename = f"{base_name}_pca_analysis.csv"
    
    # Load the CSV file
    df = pd.read_csv(input_filename)
    print(f"Loaded data shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    
    # Check if embedding column exists
    if 'embedding' not in df.columns:
        print("Error: 'embedding' column not found in the CSV file.")
        sys.exit(1)
    
    # Parse the embedding column (convert string representation to actual arrays)
    print("Parsing embeddings...")
    embeddings_list = []
    for idx, embedding_str in enumerate(df['embedding']):
        try:
            # Parse the string representation of the list
            embedding = ast.literal_eval(embedding_str)
            embeddings_list.append(embedding)
        except Exception as e:
            print(f"Error parsing embedding at row {idx}: {e}")
            continue
    
    # Convert to numpy array
    embeddings_array = np.array(embeddings_list)
    print(f"Embeddings array shape: {embeddings_array.shape}")
    
    # Standardize the features (important for PCA)
    scaler = StandardScaler()
    embeddings_scaled = scaler.fit_transform(embeddings_array)
    
    # Perform PCA
    # Let's start with keeping components that explain 95% of variance
    pca = PCA(n_components=0.95)
    principal_components = pca.fit_transform(embeddings_scaled)
    
    print(f"Original dimension: {embeddings_array.shape[1]}")
    print(f"Reduced dimension: {principal_components.shape[1]}")
    print(f"Explained variance ratio: {pca.explained_variance_ratio_[:10]}")  # Show first 10 components
    print(f"Cumulative explained variance: {np.cumsum(pca.explained_variance_ratio_)[:10]}")
    print(f"Total explained variance: {np.sum(pca.explained_variance_ratio_):.4f}")
    
    # Convert principal components back to list format for embedding column
    pca_embeddings = [pc.tolist() for pc in principal_components]
    
    # Get metadata columns (all columns except 'embedding')
    metadata_columns = [col for col in df.columns if col != 'embedding']
    
    # Create result dataframe with metadata columns and new embedding column
    result_df = df[metadata_columns].copy()
    result_df['embedding'] = pca_embeddings
    
    # Save to new CSV
    result_df.to_csv(output_filename, index=False)
    print(f"Saved PCA results to {output_filename}")
    print(f"Output shape: {result_df.shape}")
    
    # Also save PCA analysis details
    analysis_df = pd.DataFrame({
        'component': [f'PC{i+1}' for i in range(len(pca.explained_variance_ratio_))],
        'explained_variance_ratio': pca.explained_variance_ratio_,
        'cumulative_variance': np.cumsum(pca.explained_variance_ratio_)
    })
    
    analysis_df.to_csv(analysis_filename, index=False)
    print(f"Saved PCA analysis details to {analysis_filename}")

if __name__ == "__main__":
    main()