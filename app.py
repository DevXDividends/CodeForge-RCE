import streamlit as st
import streamlit_ace as sta
from codeforge import CodeForgeRCE
from models import ExecutionRequest

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

user_input = st.text_area(
    label="Input"
)

run = st.button(
    "Run code",
    type="primary"
)


if run:
    with st.spinner("Compiling and Running..."):
        request = ExecutionRequest(
            code=code,
            language="cpp",
            stdin=user_input,
            timeout=2
        )
        rce = CodeForgeRCE()
        result = rce.execute(
            request
        )
        status = result.get(
            "status"
        )
        if status == "SUCCESS":

            st.success(
                "Execution Successful"
            )

            st.code(
                result.get(
                    "stdout",
                    ""
                ),
                language="text"
            )

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    "Execution Time",
                    f"{result.get('execution_time_ms', 0)} ms"
                )

            with col2:

                st.metric(
                    "Memory Used",
                    f"{result.get('memory', 'N/A')} MB"
                )

        elif status == "COMPILATION ERROR":
            st.error(
                "Compilation Error"
            )

            st.code(
                result.get(
                    "logs",
                    "No logs available"
                ),
                language="bash"
            )
        elif status in ["TLE", "MLE"]:

            st.error(
                f"Resource Limit Exceeded: {status}"
            )

            st.code(
                result.get(
                    "stdout",
                    ""
                ),
                language="text"
            )
        else:

            st.error(
                f"Error Status: {status}"
            )

            err_output = (
                result.get("stdout")
                or result.get("logs")
                or "An unknown error occurred."
            )

            st.code(
                err_output,
                language="text"
            )