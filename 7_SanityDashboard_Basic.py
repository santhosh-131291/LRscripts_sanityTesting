import streamlit as st
import os
import subprocess
import pandas as pd
import time
import re
from concurrent.futures import ThreadPoolExecutor
import plotly.express as px

# CONFIG
MDRV = r"C:\Program Files (x86)\OpenText\LoadRunner\bin\mdrv.exe"
SCRIPTS_ROOT = r"C:\LR_Scripts"

st.set_page_config(page_title="LoadRunner Sanity Dashboard", layout="wide")

st.title("🚀 LoadRunner Sanity Test Dashboard")

# Get script folders
folders = [d for d in os.listdir(SCRIPTS_ROOT) if os.path.isdir(os.path.join(SCRIPTS_ROOT, d))]

select_all = st.checkbox("Select All Scripts")

selected_scripts = st.multiselect(
    "Select Scripts",
    folders,
    default=folders if select_all else []
)

max_threads = st.slider("Parallel Execution", 1, 10, 5)

def run_script(script):

    script_dir = os.path.join(SCRIPTS_ROOT, script)
    usr_path = os.path.join(script_dir, f"{script}.usr")
    log_path = os.path.join(script_dir, "output.txt")

    start = time.time()

    try:
        subprocess.run([MDRV, "-usr", usr_path], capture_output=True, timeout=300)
    except Exception as e:
        return {
            "Script": script,
            "Status": "EXEC_ERROR",
            "Duration": 0,
            "Total Txns": 0,
            "Failed Txns": "-",
            "Last Error": str(e)
        }

    duration = round(time.time() - start,2)

    status = "PASSED"
    txn_count = 0
    failed = []
    last_error = "-"

    if os.path.exists(log_path):

        with open(log_path,'r',errors='ignore') as f:

            content = f.read()

            txn_count = content.lower().count("ended with")

            fail_pattern = r'Transaction "([^"]+)" ended with "Fail" status'
            failed = re.findall(fail_pattern,content,re.IGNORECASE)
            

            error_pattern = r'Error\s*-\d+:\s*(.*)'
            errors = re.findall(error_pattern,content)

            if errors:
                last_error = errors[-1]

            if failed or errors:
                status="FAILED"

    return {
        "Script":script,
        "Status":status,
        "Duration (sec)":duration,
        "Total Txns":txn_count,
        "Failed Txns":", ".join(failed) if failed else "-",
        "Last Error":last_error
    }

# RUN BUTTON
if st.button("▶ Run Sanity"):

    if not selected_scripts:
        st.warning("Select scripts first")
        st.stop()

    progress = st.progress(0)
    results=[]

    total=len(selected_scripts)

    for i,script in enumerate(selected_scripts):

        result = run_script(script)

        results.append(result)

        progress.progress((i+1)/total)

    df = pd.DataFrame(results)

    st.success("Execution Completed")

    # SUMMARY
    total_scripts=len(df)
    passed=len(df[df["Status"]=="PASSED"])
    failed=len(df[df["Status"]=="FAILED"])

    col1,col2,col3 = st.columns(3)

    col1.metric("Total Scripts",total_scripts)
    col2.metric("Passed",passed)
    col3.metric("Failed",failed)

    # RESULT TABLE
    st.subheader("Execution Results")

    def highlight(val):
        if val=="FAILED":
            return "background-color:red;color:white"
        elif val=="PASSED":
            return "background-color:green;color:white"

    st.dataframe(df.style.applymap(highlight,subset=["Status"]))

    # DURATION CHART
    st.subheader("Execution Time")

    fig = px.bar(
        df,
        x="Script",
        y="Duration (sec)",
        color="Status",
        title="Script Execution Time"
    )

    st.plotly_chart(fig,use_container_width=True)

    # DOWNLOAD REPORT
    report="Sanity_Report.xlsx"
    df.to_excel(report,index=False)

    with open(report,"rb") as f:

        st.download_button(
            "Download Excel Report",
            f,
            file_name=report
        )
