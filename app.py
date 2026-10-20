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
    combined_df.columns = [str(c).strip() for c in combined_df.columns]
    return combined_df
  return pd.DataFrame()


# --- IMAGE MATCHER (SKU BASED & RECURSIVE BATCH SCAN) ---
def find_image_for_code(code_str):
  if not code_str or pd.isna(code_str):
    return None

  clean_code = str(code_str).strip()
  extensions = [".jpg", ".jpeg", ".png", ".JPG", ".PNG", ".webp"]

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
    "Search inventory by model number, view SKUs, and click the image icon to"
    " inspect individual product photos."
)

df = load_inventory_data()

if df.empty:
  st.warning(
      "⚠️ No inventory files (.xlsx, .xls, .csv) found in the root directory."
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

    # Search Query Input (Model Number / Keywords / SKU)
    search_query = st.text_input(
        "Search by Model Number, SKU, or Brand...", ""
    )

    search_results = filtered_df
    if search_query:
      mask = filtered_df.astype(str).apply(
          lambda x: x.str.contains(search_query, case=False, na=False)
      ).any(axis=1)
      search_results = filtered_df[mask]

    st.markdown(f"**Found {len(search_results)} matching records.**")

    if not search_results.empty:
      # Identify SKU column dynamically
      sku_cols = [c for c in search_results.columns if "sku" in c.lower()]
      sku_col = sku_cols[0] if sku_cols else search_results.columns[0]

      # Initialize session state for selected SKU image preview if not exists
      if "active_preview_sku" not in st.session_state:
        st.session_state.active_preview_sku = None

      # Layout: Table/List on left, Clicked SKU Image Preview on right
      left_col, right_col = st.columns([2, 1])

      with left_col:
        st.markdown(
            "#### 📋 Search Results (Click '🖼️ View' next to any SKU)"
        )

        # Display full results dataframe for reference
        st.dataframe(search_results, use_container_width=True, height=300)

        st.markdown("---")
        st.markdown("#### 🔍 SKU-by-SKU Image Inspection List")

        # Limit listing to avoid browser lag if a search returns thousands of rows
        max_display = 100
        display_subset = search_results.head(max_display)
        if len(search_results) > max_display:
          st.info(
              f"Showing first {max_display} records for interactive inspection."
              " Refine your search for specific models."
          )

        # Render interactive rows with a button/icon in front of each SKU
        for idx, row in display_subset.iterrows():
          current_sku = row[sku_col]
          # Try to grab model or description for label context
          model_cols = [
              c for c in search_results.columns if "model" in c.lower()
          ]
          model_val = (
              str(row[model_cols[0]]) if model_cols else "N/A"
          )

          cols = st.metric_col if hasattr(st, "metric_col") else st.columns([1, 3, 2])
          col_btn, col_sku, col_model = st.columns([1, 2, 3])

          with col_btn:
            if st.button("🖼️ View", key=f"btn_{idx}_{current_sku}"):
              st.session_state.active_preview_sku = current_sku

          with col_sku:
            st.markdown(f"**SKU:** `{current_sku}`")

          with col_model:
            st.text(f"Model: {model_val}")

          st.markdown("<hr style='margin:5px 0;'>", unsafe_allow_html=True)

        # CSV Download button
        csv_data = search_results.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Search Results as CSV",
            data=csv_data,
            file_name="search_results.csv",
            mime="text/csv",
        )

      with right_col:
        st.markdown("### 🖼️ Selected SKU Preview")

        if st.session_state.active_preview_sku:
          target_sku = st.session_state.active_preview_sku
          matched_img = find_image_for_code(target_sku)

          st.markdown(f"**Active SKU:** `{target_sku}`")

          if matched_img:
            st.image(
                matched_img,
                caption=f"Image for SKU: {target_sku} ({os.path.basename(matched_img)})",
                use_container_width=True,
            )
          else:
            st.warning(
                f"⚠️ Image file for SKU `{target_sku}` not found in batch"
                " folders."
            )
        else:
          st.info(
              "👈 Click the **🖼️ View** button next to any SKU on the left to"
              " inspect its picture here."
          )
    else:
      st.info("No records match your search criteria.")

  elif app_mode == "🔒 Admin Panel":
    st.subheader("Administrator Portal")

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
