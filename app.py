import os
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Frame Finder Portal", page_icon="👓", layout="wide"
)

# Directory to permanently store uploaded Excel/CSV files
DATA_DIR = "saved_frames_data"
if not os.path.exists(DATA_DIR):
  os.makedirs(DATA_DIR)


# Helper function to load all saved files from disk
def load_all_saved_files():
  files_data = {}
  if not os.path.exists(DATA_DIR):
    return files_data

  for fname in os.listdir(DATA_DIR):
    file_path = os.path.join(DATA_DIR, fname)
    if os.path.isfile(file_path):
      try:
        if fname.endswith(".csv"):
          files_data[fname] = pd.read_csv(file_path)
        elif fname.endswith((".xlsx", ".xls")):
          files_data[fname] = pd.read_excel(file_path)
      except Exception as e:
        st.error(f"Could not read permanent file {fname}: {e}")
  return files_data


# App Title
st.title("👓 Frame Finder Portal (Lifetime Edition)")
st.markdown(
    "Permanently store your Excel sheets and perform deep, flexible partial"
    " model searches across all of them."
)

# Tabs Configuration
tab_model, tab_data = st.tabs(["🔍 Frame Model", "📁 Frame Data"])

# ==========================================
# TAB 1: FRAME MODEL (Deep Search Section)
# ==========================================
with tab_model:
  st.header("Search Frame Models")

  # Load current active files from disk
  current_files_data = load_all_saved_files()

  if not current_files_data:
    st.info(
        "No frame data sheets found. Please upload your Excel sheets in the"
        " **Frame Data** tab first."
    )
  else:
    # Combine all stored dataframes for global searching
    combined_df_list = []
    for fname, df in current_files_data.items():
      temp_df = df.copy()
      temp_df["Source File"] = fname
      combined_df_list.append(temp_df)

    master_df = pd.concat(combined_df_list, ignore_index=True)

    # Search Inputs
    col1, col2 = st.columns([3, 1])
    with col1:
      search_query = st.text_input(
          "Enter Model Number, SKU, or Keyword (Partial match supported, e.g.,"
          " 'rd811'):",
          "",
      )
    with col2:
      selected_file_filter = st.selectbox(
          "Filter by Source File", ["All Sheets"] + list(current_files_data.keys())
      )

    if search_query:
      # Filter by source file if requested
      df_to_search = master_df
      if selected_file_filter != "All Sheets":
        df_to_search = master_df[master_df["Source File"] == selected_file_filter]

      # Perform deep search across all string columns case-insensitively
      mask = (
          df_to_search.astype(str)
          .apply(lambda col: col.str.contains(search_query, case=False, na=False))
          .any(axis=1)
      )

      search_results = df_to_search[mask]

      st.markdown(f"### Search Results ({len(search_results)} found)")

      if not search_results.empty:
        st.dataframe(search_results, use_container_width=True)

        # Download option for filtered results
        csv_export = search_results.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Search Results as CSV",
            data=csv_export,
            file_name="frame_search_results.csv",
            mime="text/csv",
        )
      else:
        st.warning(
            f"No matching results found for '{search_query}'. Try checking your"
            " spelling or typing a shorter segment."
        )
    else:
      st.markdown(
          "_Type a model number or keyword above to instantly search across all"
          " permanent files._"
      )

      # Preview master inventory option
      with st.expander("📊 Preview Complete Combined Inventory"):
        st.dataframe(master_df, use_container_width=True)


# ==========================================
# TAB 2: FRAME DATA (Multiple Excel Management)
# ==========================================
with tab_data:
  st.header("Permanent Frame Data Management")
  st.markdown(
      "Upload new Excel (`.xlsx`, `.xls`) or CSV sheets. Files uploaded here"
      " are saved permanently to your computer folder (`saved_frames_data`),"
      " ensuring they remain available forever."
  )

  # File Uploader supporting multiple files
  uploaded_files = st.file_uploader(
      "Upload Excel/CSV Sheets",
      type=["xlsx", "xls", "csv"],
      accept_multiple_files=True,
  )

  if uploaded_files:
    for uploaded_file in uploaded_files:
      save_path = os.path.join(DATA_DIR, uploaded_file.name)
      try:
        # Save file permanently to disk
        with open(save_path, "wb") as f:
          f.write(uploaded_file.getbuffer())
        st.success(f"Successfully saved permanent file: {uploaded_file.name}")
      except Exception as e:
        st.error(f"Error saving {uploaded_file.name}: {e}")
    # Refresh to show newly uploaded file
    st.rerun()

  # Display currently loaded permanent files and allow individual removal
  active_files = load_all_saved_files()
  if active_files:
    st.subheader("Permanent Files Stored in Portal")

    for fname in list(active_files.keys()):
      col_a, col_b, col_c = st.columns([3, 2, 1])
      with col_a:
        st.text(f"📄 {fname}")
      with col_b:
        shape = active_files[fname].shape
        st.text(f"Rows: {shape[0]}, Cols: {shape[1]}")
      with col_c:
        if st.button("Delete Permanently", key=f"del_{fname}"):
          file_to_remove = os.path.join(DATA_DIR, fname)
          if os.path.exists(file_to_remove):
            os.remove(file_to_remove)
          st.success(f"Deleted {fname}")
          st.rerun()

    if st.button("🗑️ Clear All Permanent Files"):
      for fname in list(active_files.keys()):
        file_to_remove = os.path.join(DATA_DIR, fname)
        if os.path.exists(file_to_remove):
          os.remove(file_to_remove)
      st.rerun()
  else:
    st.info("No permanent data sheets found in storage.")