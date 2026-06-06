import streamlit as st
import subprocess
from docker_workflow import execute_code
import streamlit_ace as sta

st.set_page_config(
    page_title="CODEFORGE - RCE"
)

st.header("CODEFORGE - RCE")
st.subheader("Write Your Code Here")

code = sta.st_ace(
    language="c_cpp",
    theme="monokai",
    height=500,
    auto_update=True
)

run = st.button("Run code",type="primary")
if run:
    with open("workspace/code.cpp","w")as file:
        file.write(code)
    with st.spinner("Compiling and Running..."):
        result = execute_code()
        if result["status"] == "SUCCESS":
            print(result["status_code"])
            st.success(result["logs"])
        elif result["status"] == "TLE":
            print(result["status_code"])
            st.error(result["logs"])
        elif result["status"] == "MLE":
            print(result["status_code"])
            st.error(result["logs"])
        else:
            print(result["status_code"])
            st.error(result["logs"])