import os
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Frame Finder Portal", page_icon="👓", layout="wide"
)

# Directories
DATA_DIR = "."
IMG_DIR = "images"
PASS_FILE = "admin_pass.txt"

# Ensure images directory exists locally
if not os.path.exists(IMG_DIR):
  os.makedirs(IMG_DIR)


# Helper function for password management
def get_current_password():
  if os.path.exists(PASS_FILE):
    with open(PASS_FILE, "r") as f:
      return f.read().strip()
  return "Office@880"  # Default secure password


def set_new_password(new_pass):
  with open(PASS_FILE, "w") as f:
    f.write(new_pass)


# Helper function to load all Excel/CSV inventory files
def load_all_saved_files():
  files_data = {}
  if not os.path.exists(DATA_DIR):
    return files_data

  for fname in os.listdir(DATA_DIR):
    if fname.endswith((".xlsx", ".xls", ".csv")) and not fname.startswith("."):
      file_path = os.path.join(DATA_DIR, fname)
      try:
        if fname.endswith(".csv"):
          files_data[fname] = pd.read_csv(file_path)
        else:
          files_data[fname] = pd.read_excel(file_path)
      except Exception as e:
        st.error(f"Could not read file {fname}: {e}")
  return files_data


# Helper function to find a matching image file in the 'images' folder or root
def find_image_for_code(code_str):
  if not code_str:
    return None
  clean_code = str(code_str).strip()
  extensions = [".jpg", ".jpeg", ".png", ".JPG", ".PNG", ".webp"]

  for ext in extensions:
    # Check inside the 'images' folder first (Best Practice)
    img_path = os.path.join(IMG_DIR, f"{clean_code}{ext}")
    if os.path.exists(img_path):
      return img_path
    # Fallback to root folder
    root_path = os.path.join(DATA_DIR, f"{clean_code}{ext}")
    if os.path.exists(root_path):
      return root_path

  return None


# App Title
st.title("👓 Frame Finder Portal")
st.markdown(
    "Search frame models instantly with visual previews or log into the Admin"
    " panel."
)

# Tabs Configuration
tab_model, tab_data = st.tabs(["🔍 Frame Model", "📁 Frame Data (Admin)"])

# ==========================================
# TAB 1: FRAME MODEL (Public Deep Search + Images)
# ==========================================
with tab_model:
  st.header("Search Frame Models & Preview Images")

  current_files_data = load_all_saved_files()

  if not current_files_data:
    st.warning(
        "⚠️ No Excel data sheets found. Please upload your Excel file to your"
        " GitHub repository."
    )
  else:
    combined_df_list = []
    for fname, df in current_files_data.items():
      temp_df = df.copy()
      temp_df["Source File"] = fname
      combined_df_list.append(temp_df)

    master_df = pd.concat(combined_df_list, ignore_index=True)

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
      df_to_search = master_df
      if selected_file_filter != "All Sheets":
        df_to_search = master_df[master_df["Source File"] == selected_file_filter]

      mask = (
          df_to_search.astype(str)
          .apply(lambda col: col.str.contains(search_query, case=False, na=False))
          .any(axis=1)
      )

      search_results = df_to_search[mask]

      st.markdown(f"### Search Results ({len(search_results)} found)")

      if not search_results.empty:
        table_col, img_col = st.columns([2, 1])

        with table_col:
          st.dataframe(search_results, use_container_width=True)

          csv_export = search_results.to_csv(index=False).encode("utf-8")
          st.download_button(
              label="📥 Export Search Results as CSV",
              data=csv_export,
              file_name="frame_search_results.csv",
              mime="text/csv",
          )

        with img_col:
          st.markdown("### 🖼️ Visual Preview")
          possible_code_cols = [
              c
              for c in search_results.columns
              if any(
                  k in c.lower()
                  for k in ["sku", "model", "code", "item", "article"]
              )
          ]

          matched_img = None
          if possible_code_cols:
            sample_code = search_results.iloc[0][possible_code_cols[0]]
            matched_img = find_image_for_code(sample_code)

          if not matched_img:
            matched_img = find_image_for_code(search_query)

          if matched_img:
            st.image(
                matched_img,
                caption=f"Image for: {os.path.basename(matched_img)}",
                use_container_width=True,
            )
          else:
            st.info(
                "No matching image found in the `images` folder. (Tip: Ensure"
                " your image filename matches the SKU or Model number exactly,"
                " e.g., `RD811.jpg`)"
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

      with st.expander("📊 Preview Complete Combined Inventory"):
        st.dataframe(master_df, use_container_width=True)


# ==========================================
# TAB 2: FRAME DATA (Password-Protected Admin)
# ==========================================
with tab_data:
  st.header("Admin Control Panel")

  if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

  if not st.session_state["admin_logged_in"]:
    st.warning(
        "🔒 This section is restricted to administrators. Please enter your"
        " credentials to continue."
    )

    with st.form("admin_login_form"):
      password_input = st.text_input("Admin Password", type="password")
      submit_login = st.form_submit_button("Login")

      if submit_login:
        if password_input == get_current_password():
          st.session_state["admin_logged_in"] = True
          st.success("Logged in successfully!")
          st.rerun()
        else:
          st.error("Incorrect password. Access denied.")
  else:
    col_top1, col_top2 = st.columns([4, 1])
    with col_top1:
      st.success("🔓 Logged in as Administrator")
    with col_top2:
      if st.button("Logout"):
        st.session_state["admin_logged_in"] = False
        st.rerun()

    st.markdown("---")
    st.subheader("📁 Permanent Inventory & Asset Files")
    st.info(
        "💡 **How It Works:** Place your Excel files in the main repository"
        " folder and your compressed pictures inside an **`images`** folder on"
        " GitHub. They will load permanently and never get deleted."
    )

    active_files = load_all_saved_files()
    if active_files:
      st.subheader("Currently Loaded Data Files")
      for fname in list(active_files.keys()):
        col_a, col_b = st.columns([3, 2])
        with col_a:
          st.text(f"📄 {fname}")
        with col_b:
          shape = active_files[fname].shape
          st.text(f"Rows: {shape[0]}, Cols: {shape[1]}")
    else:
      st.warning("No Excel files found in your repository.")

    st.markdown("---")
    st.subheader("🔑 Security Settings: Change Admin Password")

    with st.form("change_password_form"):
      current_pass_input = st.text_input(
          "Current Password", type="password", key="cur_pass"
      )
      new_pass_input = st.text_input(
          "New Password", type="password", key="new_pass"
      )
      confirm_pass_input = st.text_input(
          "Confirm New Password", type="password", key="conf_pass"
      )
      submit_pass = st.form_submit_button("Update Password")

      if submit_pass:
        if current_pass_input != get_current_password():
          st.error("Current password is incorrect.")
        elif not new_pass_input:
          st.error("New password cannot be empty.")
        elif new_pass_input != confirm_pass_input:
          st.error("New passwords do not match.")
        else:
          set_new_password(new_pass_input)
          st.success("Admin password successfully updated!")
