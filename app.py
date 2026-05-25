import streamlit as st
import subprocess
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
    with open("code.cpp","w")as file:
        file.write(code)
    st.spinner("Running")
    with st.spinner("Compiling and Running..."):
        result = subprocess.run(
            ["g++","code.cpp","-o","code"],
            capture_output=True,
            text=True
        )
        if result.returncode !=0:
            st.error(f"""Compilation ERROR!!  
                 {result.stderr}
                 """)       
        else:
            output = subprocess.run(
                ["code"],
                capture_output=True,
                text=True
            )
            st.success(output.stdout)