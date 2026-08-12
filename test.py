from codeforge import CodeForgeRCE
from models import ExecutionRequest


def run_test(name, code, stdin=None, timeout=2):

    print("\n" + "=" * 60)
    print(f"TEST: {name}")
    print("=" * 60)

    rce = CodeForgeRCE()

    request = ExecutionRequest(
        code=code,
        language="cpp",
        stdin=stdin,
        timeout=timeout,
    )

    result = rce.execute(request)

    print("Status       :", result.get("status"))
    print("Status Code  :", result.get("status_code"))
    print("Output       :", repr(result.get("stdout")))
    print("Time (ms)     :", result.get("execution_time_ms"))
    print("Memory (MB)   :", result.get("memory"))

    return result


# ============================================================
# 1. BASIC SUCCESS
# ============================================================

run_test(
    "Basic Success",
    r'''
#include <iostream>

int main() {
    std::cout << "Hello CodeForge";
    return 0;
}
'''
)


# ============================================================
# 2. SUCCESS WITH MULTI-LINE OUTPUT
# ============================================================

run_test(
    "Multi-line Output",
    r'''
#include <iostream>

int main() {
    std::cout << "Hello\n";
    std::cout << "CodeForge\n";
    std::cout << "RCE\n";
    return 0;
}
'''
)


# ============================================================
# 3. INPUT SUPPORT
# ============================================================

run_test(
    "Input Support",
    r'''
#include <iostream>

int main() {

    int a, b;

    std::cin >> a >> b;

    std::cout << a + b;

    return 0;
}
''',
    stdin="10 20"
)


# ============================================================
# 4. MULTI-LINE INPUT
# ============================================================

run_test(
    "Multi-line Input",
    r'''
#include <iostream>

int main() {

    int n;
    std::cin >> n;

    int sum = 0;

    for (int i = 0; i < n; i++) {
        int x;
        std::cin >> x;
        sum += x;
    }

    std::cout << sum;

    return 0;
}
''',
    stdin="""5
1 2 3 4 5
"""
)


# ============================================================
# 5. NO INPUT PROVIDED
# ============================================================

run_test(
    "No Input",
    r'''
#include <iostream>

int main() {
    std::cout << "No input required";
    return 0;
}
'''
)


# ============================================================
# 6. INPUT PROVIDED BUT PROGRAM DOESN'T USE IT
# ============================================================

run_test(
    "Unused Input",
    r'''
#include <iostream>

int main() {
    std::cout << "Input ignored";
    return 0;
}
''',
    stdin="""100
200
300
"""
)


# ============================================================
# 7. COMPILATION ERROR
# ============================================================

run_test(
    "Compilation Error",
    r'''
#include <iostream>

int main() {
    std::cout << "Hello"
    return 0;
}
'''
)


# ============================================================
# 8. SEGMENTATION FAULT
# ============================================================

run_test(
    "Segmentation Fault",
    r'''
#include <iostream>

int main() {

    int* ptr = nullptr;

    *ptr = 100;

    return 0;
}
'''
)


# ============================================================
# 9. ABORT
# ============================================================

run_test(
    "Abort",
    r'''
#include <cstdlib>

int main() {

    abort();

    return 0;
}
'''
)


# ============================================================
# 10. FLOATING POINT EXCEPTION
# ============================================================

run_test(
    "Floating Point Exception",
    r'''
#include <iostream>

int main() {

    volatile int a = 10;
    volatile int b = 0;

    int c = a / b;

    std::cout << c;

    return 0;
}
'''
)


# ============================================================
# 11. TLE
# ============================================================

run_test(
    "Time Limit Exceeded",
    r'''
int main() {

    while (true) {
    }

    return 0;
}
''',
    timeout=2
)


# ============================================================
# 12. TLE WITH INPUT
# ============================================================

run_test(
    "TLE With Input",
    r'''
#include <iostream>

int main() {

    int n;
    std::cin >> n;

    while (true) {
    }

    return 0;
}
''',
    stdin="100",
    timeout=2
)


# ============================================================
# 13. MEMORY LIMIT EXCEEDED
# ============================================================

run_test(
    "Memory Limit Exceeded",
    r'''
#include <vector>

int main() {

    std::vector<int> data;

    while (true) {
        data.resize(data.size() + 1000000);
    }

    return 0;
}
''',
    timeout=5
)


# ============================================================
# 14. LARGE OUTPUT
# ============================================================

run_test(
    "Large Output",
    r'''
#include <iostream>

int main() {

    for (int i = 0; i < 100000; i++) {
        std::cout << "CodeForge\n";
    }

    return 0;
}
'''
)


# ============================================================
# 15. TWO SUM REALISTIC TEST
# ============================================================

run_test(
    "Two Sum",
    r'''
#include <iostream>
#include <vector>
#include <unordered_map>

using namespace std;

class Solution {

public:

    vector<int> twoSum(
        vector<int>& nums,
        int target
    ) {

        unordered_map<int, int> mpp;

        for (int i = 0; i < nums.size(); i++) {

            int complement = target - nums[i];

            if (mpp.find(complement) != mpp.end()) {
                return {
                    mpp[complement],
                    i
                };
            }

            mpp[nums[i]] = i;
        }

        return {};
    }
};


int main() {

    int n;
    cin >> n;

    vector<int> nums(n);

    for (int i = 0; i < n; i++) {
        cin >> nums[i];
    }

    int target;
    cin >> target;

    Solution solution;

    vector<int> result =
        solution.twoSum(nums, target);

    for (int i = 0; i < result.size(); i++) {

        if (i > 0)
            cout << " ";

        cout << result[i];
    }

    cout << "\n";

    return 0;
}
''',
    stdin="""4
2 7 11 15
9
"""
)