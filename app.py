import streamlit as st
import json
import os
import pandas as pd
from azure.storage.blob import BlobServiceClient
from blob_storage import download_pdf_from_blob
from openai_service import send_to_openai
from pdf_processing import extract_text_from_pdf, format_to_structure, parse_content_to_json, remove_outside_braces
from utils import json_to_excel, txttojson
import io
import base64
import yaml
from PIL import Image
import time
import matplotlib.pyplot as plt

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# Azure Blob Storage configuration
# storage_connection_string = config['azure_storage']['storage_connection_string']
# evaluation_container_name = config['azure_storage']['evaluation_container_name']
# evaluation_excel_blob_name = "Evaluation_Montefiore - NTTD - IT Outsourcing - MSA_7_14.xlsx"
storage_connection_string = st.secrets["azure_storage"]["storage_connection_string"]
evaluation_container_name = st.secrets["azure_storage"]["evaluation_container_name"]

# Define the output directory (inside the "Insights" folder)
output_dir = os.path.join("Insights")
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Initialize session state
if "excel_path" not in st.session_state:
    st.session_state.excel_path = None
if "processing" not in st.session_state:
    st.session_state.processing = False
if "view_pdf" not in st.session_state:
    st.session_state.view_pdf = False
if "pdf_base64" not in st.session_state:
    st.session_state.pdf_base64 = None
if "excel_generated" not in st.session_state:
    st.session_state.excel_generated = False
if "insights_generated" not in st.session_state:
    st.session_state.insights_generated = False

# Function to list containers and blobs
def list_containers():
    try:
        blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
        container_list = blob_service_client.list_containers()
        return [container.name for container in container_list]
    except Exception as e:
        st.error(f"Error fetching containers: {e}")
        return []

def list_blobs(container_name):
    try:
        container_client = BlobServiceClient.from_connection_string(storage_connection_string).get_container_client(container_name)
        blob_list = container_client.list_blobs()
        return [blob.name for blob in blob_list if blob.name.endswith(".pdf")]
    except Exception as e:
        st.error(f"Error fetching blobs: {e}")
        return []

# Streamlit UI
st.set_page_config(page_title="DocsInSight", page_icon=":book:", layout="wide")

def download_evaluation_file_from_azure_blob(evaluation_container_name, evaluation_excel_blob_name, download_path):
    """Download file from Azure Blob Storage."""
    try:
        blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
        container_client = blob_service_client.get_container_client(evaluation_container_name)
        blob_client = container_client.get_blob_client(evaluation_excel_blob_name)

        with open(download_path, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())

        return True
        
    except Exception as e:
        st.warning(f"No file is available in Azure Blob Storage for comparison.\n\n"
             "Required Information:\n"
             "- The file name must follow this format: **Evaluation_{file_nm}.xlsx**, where **{file_nm}** is the specific file name you are looking to compare.\n"
             f"- The file should be located in the **{evaluation_container_name}** container within the **Azure Blob Storage** account.\n"
             "- Ensure that the file is uploaded and accessible in the correct location, as only files in this container will be considered for comparison.\n"
             "- Double-check that the file follows the naming convention and exists in the specified container.")
        return False

def load_data(file1, file2):
    """Load the Excel sheets and strip column names of whitespace."""
    try:
        df1 = pd.read_excel(file1, sheet_name=None)
        df2 = pd.read_excel(file2, sheet_name=None)
    except Exception as e:
        st.error(f"Error loading Excel files: {e}")
        return None, None

    df1 = df1[list(df1.keys())[0]]
    df2 = df2[list(df2.keys())[0]]
    
    df1.columns = df1.columns.str.strip()
    df2.columns = df2.columns.str.strip()

    return df1, df2

def calculate_metrics(TP, FP, FN, TN, total_cells):
    """Calculate and return accuracy, recall, precision, and F1 score."""
    Accuracy = (TP + TN) / total_cells if total_cells > 0 else 0
    Recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    Precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    F1_Score = 2 * (Precision * Recall) / (Precision + Recall) if (Precision + Recall) > 0 else 0
    return Accuracy, Recall, Precision, F1_Score

def compare_dataframes(df1, df2, columns_to_compare):
    """Compare two dataframes and return the metrics and non-relevant data."""
    TP = FP = FN = TN = 0
    non_relevant_data = []

    # Check for missing columns
    missing_columns = [col for col in columns_to_compare if col not in df1.columns or col not in df2.columns]
    if missing_columns:
        st.warning(f"Warning: Missing Columns in the Data – [{', '.join(missing_columns)}]")
        columns_to_compare = [col for col in columns_to_compare if col not in missing_columns]

    # Group by 'Reference' to compare row by row
    grouped_df1 = df1.groupby('Reference')
    grouped_df2 = df2.groupby('Reference')

    for reference, group1 in grouped_df1:
        group2 = grouped_df2.get_group(reference) if reference in grouped_df2.groups else pd.DataFrame()

        for (idx1, row1), (idx2, row2) in zip(group1.iterrows(), group2.iterrows()):
            for col in columns_to_compare:
                if col in row1 and col in row2:
                    val1 = row1[col]
                    val2 = row2[col]

                    if pd.isna(val1) and pd.isna(val2):
                        TP += 1
                    elif pd.isna(val1) or pd.isna(val2):
                        FP += 1
                        FN += 1
                        non_relevant_data.append((val1, val2, col, reference))
                    elif val1 == val2:
                        TP += 1
                    else:
                        FP += 1
                        FN += 1
                        non_relevant_data.append((val1, val2, col, reference))

                    if not pd.isna(val1) and not pd.isna(val2) and val1 != val2:
                        TN += 1

    total_cells = len(df1) * len(columns_to_compare)
    Accuracy, Recall, Precision, F1_Score = calculate_metrics(TP, FP, FN, TN, total_cells)
    
    return Accuracy, Recall, Precision, F1_Score, TP, FP, FN, TN, non_relevant_data

def evaluation(file2, columns_to_compare):
    """Evaluation function triggered by Streamlit button."""
    start_time = time.time()

    local_file1 = 'Insights/evaluation_excel.xlsx'
    if not download_evaluation_file_from_azure_blob(evaluation_container_name, evaluation_excel_blob_name, local_file1):
        return

    df1, df2 = load_data(local_file1, file2)
    if df1 is None or df2 is None:
        return

    # Check if dataframes are identical
    if df1.equals(df2):
        st.success("Both DataFrames are identical!")
        TP = len(df1) * len(columns_to_compare)  # All cells match, so TP = total cells
        FP = FN = TN = 0
        Accuracy, Recall, Precision, F1_Score = calculate_metrics(TP, FP, FN, TN, TP)
        display_results(Accuracy, Recall, Precision, F1_Score, TP, FP, FN, TN)
    else:
        Accuracy, Recall, Precision, F1_Score, TP, FP, FN, TN, non_relevant_data = compare_dataframes(df1, df2, columns_to_compare)
        display_results(Accuracy, Recall, Precision, F1_Score, TP, FP, FN, TN)
        display_non_relevant_data(non_relevant_data)

    end_time = time.time()
    execution_time = end_time - start_time
    st.write(f"Execution Time: {execution_time:.2f} seconds")

    # Cleanup
    try:
        os.remove(local_file1)
    except Exception as e:
        pass


def display_results(Accuracy, Recall, Precision, F1_Score, TP, FP, FN, TN):
    """Display the evaluation results in Streamlit and place the chart on the right side."""
    with st.expander("Evaluation Results", expanded=True):
    # Create two columns: one for the text and one for the chart
        col1, col2 = st.columns([2, 2])  # The second column is smaller (1), so the chart is smaller
        
        with col1:
            # Display evaluation metrics as text
            st.write(f"**Accuracy**: {Accuracy:.4f}")
            st.write(f"**Recall**: {Recall:.4f}")
            st.write(f"**Precision**: {Precision:.4f}")
            st.write(f"**F1 Score**: {F1_Score:.4f}")
            st.write(f"**True Positives (TP)**: {TP}")
            st.write(f"**False Positives (FP)**: {FP}")
            st.write(f"**False Negatives (FN)**: {FN}")
            st.write(f"**True Negatives (TN)**: {TN}")

        with col2:
            # Create a bar chart for the metrics
            fig, ax = plt.subplots(figsize=(5, 2.5))  # Adjust the size for the right column
            metrics = ['Accuracy', 'Recall', 'Precision', 'F1 Score']
            values = [Accuracy, Recall, Precision, F1_Score]

            ax.bar(metrics, values, color=['#A6C8FF', '#FFB84D', '#80E0A7', '#FF7F7F'])
            ax.set_title('Evaluation Metrics')
            ax.set_ylim(0, 1)
            ax.set_ylabel('Score')

            # Display the chart using Streamlit
            st.pyplot(fig)


def display_non_relevant_data(non_relevant_data):
    """Display non-relevant data (mismatches) in Streamlit."""
    if non_relevant_data:
        st.write("**Non-Relevant Data (Mismatches):**")
        for val1, val2, col, reference in non_relevant_data:
            st.write(f"Reference: {reference}, Column: {col}, Expected: {val1}, Generated: {val2}")

# Left Sidebar for file selection and control buttons

with st.sidebar:
    # Display Logo and Title
    # img = Image.open("Assets/ntt_data.png")
    # img_resized = img.resize((250, 70))
    # st.image(img_resized)

    # **Configuration Section with Light Border**
    # with st.expander("Configuration", expanded=True):
    #     st.markdown(f"""
    #         <div style="padding: 10px;">
    #         <p><strong>Model: </strong><span style="text-transform: uppercase;">{config['openai']['model']}</span></p>
    #         <p><strong>Deployment Name: </strong><span style="text-transform: uppercase;">{config['openai']['deployment_name']}</span></p>
    #         <p><strong>Version: </strong>{config['openai']['api_version']}</p>
    #         </div>
    #     """, unsafe_allow_html=True)

    with st.expander("Configuration", expanded=True):
        st.markdown(f"""
            <div style="padding: 10px;">
            <p><strong>Model: </strong><span style="text-transform: uppercase;">{st.secrets["openai"]["model"]}</span></p>
            <p><strong>Deployment Name: </strong><span style="text-transform: uppercase;">{st.secrets["openai"]["deployment_name"]}</span></p>
            <p><strong>Version: </strong>{st.secrets["openai"]["api_version"]}</p>
            </div>
        """, unsafe_allow_html=True)

    containers = list_containers()
    if containers:
        selected_container = st.selectbox("Select Container", containers)
        if selected_container:
            blobs = list_blobs(selected_container)
            if blobs:
                selected_blob = st.selectbox("Select PDF File", blobs)
                base_blob_name = selected_blob.replace(".pdf", "")

                # Set the evaluation excel file name dynamically
                evaluation_excel_blob_name = f"Evaluation_{base_blob_name}.xlsx"
                
                if selected_blob:
                    pdf_data = download_pdf_from_blob(storage_connection_string, selected_container, selected_blob)
                    if pdf_data:
                        if isinstance(pdf_data, io.BytesIO):
                            pdf_data = pdf_data.read()
                        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
                        st.session_state.pdf_base64 = pdf_base64
                        st.session_state.view_pdf = True

                    # Generate and Cancel buttons in columns for layout
                    cols = st.columns([3, 1])
                    with cols[0]:
                        if st.button("Generate Insights") and not st.session_state.insights_generated:
                            st.session_state.processing = True
                            st.session_state.insights_generated = True
                            # Start processing the PDF (use existing logic here...)
                    
                    with cols[1]:
                        if st.button("Cancel"):
                            st.session_state.processing = False
                            st.session_state.insights_generated = False
            else:
                st.error(f"No PDF files found in container {selected_container}.")
    else:
        st.error("No containers found. Please check the Azure Blob Storage configuration.")

    with st.expander("Instructions - How to Use DocuSights"):
        st.markdown(f"""
        **Step 1: Select a Container**
        - Choose a container from Azure Blob Storage that holds your PDF files. This will allow you to access the PDF files stored inside.

        **Step 2: Choose a PDF File**
        - After selecting a container, a list of available PDF files will be displayed. Pick the PDF you want to analyze.

        **Step 3: Generate Insights**
        - Once you have selected a PDF file, click the **"Generate Insights"** button. The app will process the document and extract key insights.

        **Step 4: Evaluate Document (Optional)**
        - If you'd like to evaluate the content of your PDF against an existing Excel file, enter the relevant column names for comparison and click **"Evaluate"**.
        - The Evaluation File must be named **Evaluation_FILE_NAME.xlsx** and located in the **{evaluation_container_name}** container in **Azure Blob Storage**.
        
        **Step 5: Download Insights**
        - Once insights are generated, the results will be displayed. You can download them as an Excel file for further use.
    """)


# Right Sidebar for PDF Preview and Processing
# img2 = Image.open("Assets/ntt_data.png")
# img_resized2 = img2.resize((150, 40))
# st.image(img_resized2)

# st.markdown("""
# <div style="margin-top: -10px;">
#     <h1 style="color: black; font-weight: bold; font-size: 40px; margin-bottom: -22px;">DocuSights</h1>
#     <p style="margin-bottom: 30px; font-weight: bold; font-size: 12px;">A quick insights into your documents</p>
# </div>
# """, unsafe_allow_html=True)


# Open and resize the image
img2 = Image.open("Assets/ntt_data.png")
img_resized2 = img2.resize((150, 40))

# Create two columns: one for the image and one for the text
col1, col2 = st.columns([1, 1.35])  # Adjust the column width ratio (1:4)

with col1:
    # Display the resized image
    st.image(img_resized2)

with col2:
    # Display the text beside the image
    st.markdown("""
    <div style="margin-top: -38px;">
        <h1 style="color: black; font-weight: bold; font-size: 43px; margin-bottom: -24px;">DocsInSight</h1>
        <p style="margin-bottom: 30px; font-weight: bold; font-size: 14px;">A quick insights into your documents</p>
    </div>
    """, unsafe_allow_html=True)


st.markdown(f"""
    <div style="margin-bottom: 0px;">
        <b>Selected PDF File: </b> <span style="color: chocolate;">{selected_blob}</span>
    </div>
    """, unsafe_allow_html=True)

with st.expander("PDF Preview", expanded=False):
    if st.session_state.view_pdf:
        # st.markdown(f"**Selected PDF File:** `{selected_blob}`")
        st.markdown(f'<iframe src="data:application/pdf;base64,{st.session_state.pdf_base64}" width="700" height="600" type="application/pdf"></iframe>', unsafe_allow_html=True)

# Processing section
if st.session_state.processing:
    progress_bar = st.progress(0)
    total_steps = 5
    step_counter = 0
    process_text = st.empty()
    process_text.text("Processing...")

    try:
        pdf_data = download_pdf_from_blob(storage_connection_string, selected_container, selected_blob)
        if pdf_data:
            step_counter += 1
            progress_bar.progress(step_counter / total_steps)

            raw_text = extract_text_from_pdf(pdf_data)
            step_counter += 1
            progress_bar.progress(step_counter / total_steps)

            sections = format_to_structure(raw_text)
            step_counter += 1
            progress_bar.progress(step_counter / total_steps)

            content1 = parse_content_to_json(sections)
            step_counter += 1
            progress_bar.progress(step_counter / total_steps)

            insights_data = []
            for section, content in content1.items():
                if isinstance(content, dict):
                    for subsection, details in content.items():
                        if subsection == "No Subsection":
                            subsection = section
                        if details:
                            bullet_points = "\n".join(f"- {item}" for item in details)
                            subsection_str = f"section_name: {section}\nsubsection_name:{subsection}\nbulletpoints:\n{bullet_points}\n"
                            section_str = subsection_str
                            response = send_to_openai(section_str)
                            clean_response = remove_outside_braces(response)
                            if clean_response:
                                data = json.loads(clean_response)
                                char_limit = 1000
                                clause_text_lines = data.get("Clause Text", [])
                                if not isinstance(clause_text_lines, list):
                                    clause_text_lines = [clause_text_lines]

                                new_clause_text = []
                                notes_text = ""
                                current_length = 0
                                for line in clause_text_lines:
                                    line_length = len(line)
                                    if current_length + line_length <= char_limit:
                                        new_clause_text.append(line)
                                        current_length += line_length
                                    else:
                                        notes_text += line + " "

                                data["Clause Text"] = new_clause_text
                                data["Notes"] = notes_text.strip()

                                with open(f"{base_blob_name}.txt", "a") as f:
                                    f.write(f"\n{json.dumps(data, indent=4)}")

            output_excel_file = os.path.join(output_dir, f"Insights_{base_blob_name}.xlsx")

            # Check if the file exists, and if so, delete it
            if os.path.exists(output_excel_file):
                os.remove(output_excel_file)

            response = txttojson(f"{base_blob_name}.txt")
            if response:
                json_to_excel(response, output_excel_file, selected_blob)
                step_counter += 1
                progress_bar.progress(step_counter / total_steps)
                process_text.text("✅ Insights Successfully Generated.")
                st.session_state.excel_path = output_excel_file
                st.session_state.excel_generated = True

    except Exception as e:
        st.error(f"Error during processing: {e}")
        st.session_state.processing = False

# Excel file preview and download
if st.session_state.excel_generated:

    cols = st.columns([4, 1])  # Adjust the width ratio of the columns as needed
    
    with cols[0]:
        st.markdown(f"""
        <div>
            <b>Insights is available at: </b> 
            <span style="color: chocolate;">📂Insights/{os.path.basename(st.session_state.excel_path)}</span>
        </div>
        """, unsafe_allow_html=True)

    with cols[1]:
        # Download button in the second column, aligned to the right
        with open(st.session_state.excel_path, "rb") as file:
            excel_data = file.read()

        st.download_button(
            label="Download Insights",
            data=excel_data,
            file_name=os.path.basename(st.session_state.excel_path),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with open(st.session_state.excel_path, "rb") as file:
        excel_data = file.read()

    excel_file = io.BytesIO(excel_data)
    df = pd.read_excel(excel_file, engine='openpyxl')
    st.dataframe(df)

    st.session_state.processing = False
    st.session_state.insights_generated = False

    file2 = f"Insights/Insights_{base_blob_name}.xlsx"
    st.markdown("<h4 style='font-weight: bold;'>Evaluatation</h4>", unsafe_allow_html=True)
    columns_input = st.text_area("**Enter the columns to evaluate (comma separated)**", 
                                'Major Area, Reference, Manager, Owner, Status, Risk, Frequency, Category, Clause Text, Notes, Comments, Task Description')

    columns_to_compare = [col.strip() for col in columns_input.split(',')]

    if file2 is not None and st.button("Evaluate"):
        evaluation(file2, columns_to_compare)
