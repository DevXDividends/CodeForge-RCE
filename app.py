import streamlit as st
import streamlit_ace as sta

from codeforge import CodeForgeRCE
from models import ExecutionRequest


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CODEFORGE - RCE"
)


# ============================================================
# UI
# ============================================================

st.header("CODEFORGE - RCE")
st.subheader("Write Your Code Here")


code = sta.st_ace(
    language="c_cpp",
    theme="monokai",
    height=500,
    auto_update=True,
)


user_input = st.text_area(
    label="Input",
    placeholder="Enter program input here..."
)


run = st.button(
    "Run code",
    type="primary",
)


# ============================================================
# EXECUTION
# ============================================================

if run:

    # ----------------------------------------
    # Validate code
    # ----------------------------------------

    if not code or not code.strip():

        st.error("Please enter some code.")

        st.stop()

    # ----------------------------------------
    # Execute
    # ----------------------------------------

    with st.spinner(
        "Compiling and Running..."
    ):

        # Create execution request
        request = ExecutionRequest(
            code=code,
            language="cpp",
            stdin=user_input,
            timeout=2,
        )

        # Create RCE engine
        rce = CodeForgeRCE()

        # Execute request
        result = rce.execute(
            request
        )

    # ----------------------------------------
    # Extract status
    # ----------------------------------------

    status = result.get(
        "status"
    )


    # ========================================================
    # SUCCESS
    # ========================================================

    if status == "SUCCESS":

        st.success(
            "Execution Successful"
        )

        # Program output
        stdout = result.get(
            "stdout",
            ""
        )

        st.code(
            stdout,
            language="text"
        )

        # Metrics
        col1, col2 = st.columns(2)

        with col1:

            execution_time = result.get(
                "execution_time_ms",
                0
            )

            st.metric(
                "Execution Time",
                f"{execution_time} ms"
            )

        with col2:

            memory = result.get(
                "memory",
                "N/A"
            )

            st.metric(
                "Memory Used",
                f"{memory} MB"
            )


    # ========================================================
    # COMPILATION ERROR
    # ========================================================

    elif status == "COMPILATION ERROR":

        st.error(
            "Compilation Error"
        )

        logs = result.get(
            "logs",
            "No logs available"
        )

        st.code(
            logs,
            language="bash"
        )


    # ========================================================
    # TLE / MLE
    # ========================================================

    elif status in [
        "TLE",
        "MLE",
    ]:

        st.error(
            f"Resource Limit Exceeded: {status}"
        )

        output = result.get(
            "stdout",
            ""
        )

        st.code(
            output,
            language="text"
        )


    # ========================================================
    # OTHER ERRORS
    # ========================================================

    else:

        st.error(
            f"Error Status: {status}"
        )

        error_output = (
            result.get("stdout")
            or result.get("logs")
            or "An unknown error occurred."
        )

        st.code(
            error_output,
            language="text"
        )