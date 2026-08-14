from codeforge import CodeForgeRCE, ExecutionRequest


def run(name, code, stdin=None, timeout=2, language="cpp"):
    print("\n" + "=" * 50)
    print(name)
    print("=" * 50)

    rce = CodeForgeRCE()

    request = ExecutionRequest(
        code=code,
        language=language,
        stdin=stdin,
        timeout=timeout,
    )

    result = rce.execute(request)

    print(result)
    return result


# Compilation error
run(
    "Compilation Error",
    r'''
#include <iostream>

int main() {
    std::cout << "Hello"
    return 0;
}
'''
)


# Segmentation fault
run(
    "Segmentation Fault",
    r'''
int main() {
    int* p = nullptr;
    *p = 10;
}
'''
)


# TLE
run(
    "TLE",
    r'''
int main() {
    while (true) {}
}
''',
    timeout=2
)


# Unsupported language
run(
    "Unsupported Language",
    "print('hello')",
    language="python"
)