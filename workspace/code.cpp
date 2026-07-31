#include <iostream>
#include <vector>
#include <unordered_map>

using namespace std;

class Solution
{
public:
    vector<int> twoSum(vector<int> &nums, int target)
    {
        unordered_map<int, int> mpp;
        int comp = 0;
        for (int i = 0; i < nums.size(); i++)
        {
            comp = target - nums[i];
            if (mpp.find(comp) != mpp.end())
            {
                return {mpp[comp], i};
            }
            mpp[nums[i]] = i;
        }
        return {};
    }
};

int main()
{
    int nums_n;
    if (cin >> nums_n)
    {
        vector<int> nums(nums_n);
        for (int i = 0; i < nums_n; i++)
        {
            cin >> nums[i];
        }

        int target;
        cin >> target;

        Solution obj;
        auto ans = obj.twoSum(nums, target);

        for (size_t i = 0; i < ans.size(); i++)
        {
            cout << ans[i] << (i == ans.size() - 1 ? "" : " ");
        }
        cout << "\n";
    }
    return 0;
}