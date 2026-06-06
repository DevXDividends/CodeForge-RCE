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

                return {i, mpp[comp]};

            }



            mpp[nums[i]] = i;

        }



        return {};

    }

};



int main()

{



    vector<int> nums = {

        12, 45, 78, 23, 56, 89, 34, 67, 91, 14,

        38, 72, 19, 84, 53, 27, 61, 95, 40, 11,

        66, 29, 74, 88, 31, 57, 93, 16, 42, 80,

        25, 69, 99, 36, 58, 77, 13, 47, 82, 21,

        64, 90, 33, 71, 18, 54, 86, 24, 60, 97,

        15, 39, 73, 28, 55, 92, 35, 68, 10, 44,

        81, 26, 59, 94, 32, 70, 17, 52, 87, 30,

        63, 96, 20, 48, 79, 37, 62, 85, 22, 51,

        100, 41, 65, 98, 43, 76, 49, 83, 50, 75,

        1, 2, 3, 4, 5, 6, 7, 8, 9, 200};

    int target = 209;



    Solution obj;



    vector<int> result = obj.twoSum(nums, target);



    if (!result.empty())

    {

        cout << "Indices are: ";

        cout << result[0] << " " << result[1] << endl;

    }

    else

    {

        cout << "No solution found" << endl;

    }

    return 0;

}   