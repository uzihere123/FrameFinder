import os
import pandas as pd
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Frame Finder - Inventory Portal",
    page_icon="👓",
    layout="wide",
)

# --- DIRECTORIES & FILES ---
IMG_DIR = "images"
ADMIN_PASS_FILE = "admin_pass.txt"
DEFAULT_ADMIN_PASS = "Office@880"


# --- PASSWORD MANAGEMENT ---
def get_admin_password():
  if os.path.exists(ADMIN_PASS_FILE):
    with open(ADMIN_PASS_FILE, "r") as f:
      pwd = f.read().strip()
      if pwd:
        return pwd
  return DEFAULT_ADMIN_PASS


def set_admin_password(new_password):
  with open(ADMIN_PASS_FILE, "w") as f:
    f.write(new_password.strip())


# --- DATA LOADING ---
@st.cache_data
def load_inventory_data():
  all_data = []
  # Scan root directory for Excel and CSV files
  for file in os.listdir("."):
    if file.endswith((".xlsx", ".xls")):
      try:
        df = pd.read_excel(file)
        df["Source_File"] = file
        all_data.append(df)
      except Exception as e:
        st.error(f"Error loading {file}: {e}")
    elif file.endswith(".csv"):
      try:
        df = pd.read_csv(file)
        df["Source_File"] = file
        all_data.append(df)
      except Exception as e:
        st.error(f"Error loading {file}: {e}")

  if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    # Standardize column names string strip
    combined_df.columns = [str(c).strip() for c in combined_df.columns]
    return combined_df
  return pd.DataFrame()


# --- IMAGE MATCHER (SKU BASED & RECURSIVE BATCH SCAN) ---
def find_image_for_code(code_str):
  if not code_str or pd.isna(code_str):
    return None

  clean_code = str(code_str).strip()
  extensions = [".jpg", ".jpeg", ".png", ".JPG", ".PNG", ".webp"]

  # Recursively scan 'images' root and all batch subfolders (e.g., batch_001, batch_002)
  if os.path.exists(IMG_DIR):
    for root, dirs, files in os.walk(IMG_DIR):
      for ext in extensions:
        target_filename = f"{clean_code}{ext}"
        if target_filename in files:
          return os.path.join(root, target_filename)

  return None


# --- MAIN APP LAYOUT ---
st.title("👓 Frame Finder Inventory Portal")
st.markdown(
    "Search through combined inventory databases and view dynamic SKU-based"
    " product previews."
)

df = load_inventory_data()

if df.empty:
  st.warning(
      "⚠️ No inventory files (.xlsx, .xls, .csv) found in the root repository"
      " directory. Please add your spreadsheets."
  )
else:
  # Sidebar Navigation & Admin Login
  st.sidebar.title("Navigation")
  app_mode = st.sidebar.radio("Go to", ["🔍 Search Inventory", "🔒 Admin Panel"])

  if app_mode == "🔍 Search Inventory":
    st.subheader("Public Inventory Search")

    # Source File Filter
    source_files = ["All Files"] + list(df["Source_File"].unique())
    selected_source = st.sidebar.selectbox(
        "Filter by Inventory File", source_files
    )

    filtered_df = df.copy()
    if selected_source != "All Files":
      filtered_df = filtered_df[
          filtered_df["Source_File"] == selected_source
      ]

    # Search Query Input
    search_query = st.text_input(
        "Search by SKU, Model, Brand, or Keywords...", ""
    )

    search_results = filtered_df
    if search_query:
      # Global fuzzy/text matching across columns
      mask = filtered_df.astype(str).apply(
          lambda x: x.str.contains(search_query, case=False, na=False)
      ).any(axis=1)
      search_results = filtered_df[mask]

    st.markdown(f"**Found {len(search_results)} matching records.**")

    if not search_results.empty:
      # Split layout: Table on the left, Image Preview on the right
      table_col, img_col = st.columns([2, 1])

      with table_col:
        st.dataframe(search_results, use_container_width=True, height=450)

        # CSV Download button for results
        csv_data = search_results.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Search Results as CSV",
            data=csv_data,
            file_name="search_results.csv",
            mime="text/csv",
        )

      with img_col:
        st.markdown("### 🖼️ Visual Preview")

        matched_img = None
        sku_value = None

        # 1. Prioritize looking up by explicit 'SKU' column value from the first row
        sku_cols = [c for c in search_results.columns if "sku" in c.lower()]
        if sku_cols:
          sku_value = search_results.iloc[0][sku_cols[0]]
          matched_img = find_image_for_code(sku_value)

        # 2. Fallback: Search using the literal search query text if SKU match fails
        if not matched_img and search_query:
          matched_img = find_image_for_code(search_query)

        if matched_img:
          st.image(
              matched_img,
              caption=(
                  f"Matched SKU: {sku_value or search_query}"
                  f" ({os.path.basename(matched_img)})"
              ),
              use_container_width=True,
          )
        else:
          st.info(
              "ℹ️ No image found matching this SKU. Ensure image filenames in"
              " batch folders match the SKU exactly (e.g., `100082.jpg`)."
          )
    else:
      st.info("No records match your search criteria.")

  elif app_mode == "🔒 Admin Panel":
    st.subheader("Administrator Portal")

    # Session state initialization for login
    if "admin_logged_in" not in st.session_state:
      st.session_state.admin_logged_in = False

    current_admin_pass = get_admin_password()

    if not st.session_state.admin_logged_in:
      password_input = st.text_input(
          "Enter Admin Password", type="password", key="admin_pwd_input"
      )
      if st.button("Login"):
        if password_input == current_admin_pass:
          st.session_state.admin_logged_in = True
          st.success("Logged in successfully!")
          st.rerun()
        else:
          st.error("Incorrect password.")
    else:
      st.success("🔓 Logged in as Administrator")

      if st.button("Logout"):
        st.session_state.admin_logged_in = False
        st.rerun()

      st.markdown("---")
      st.markdown("### 🛠️ Admin Controls & File Management")
      st.write(
          "Upload new inventory sheets to the root directory or update system"
          " settings below."
      )

      # Password Change Section
      with st.expander("🔑 Change Admin Password"):
        new_pass = st.text_input(
            "New Admin Password", type="password", key="new_pwd"
        )
        confirm_pass = st.text_input(
            "Confirm New Password", type="password", key="conf_pwd"
        )
        if st.button("Update Password"):
          if new_pass and new_pass == confirm_pass:
            set_admin_password(new_pass)
            st.success("Admin password updated successfully!")
          else:
            st.error("Passwords do not match or field is empty.")
