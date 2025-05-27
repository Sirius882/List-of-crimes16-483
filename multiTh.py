import pandas as pd
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
import threading

# 测试模式配置
TEST_MODE = False  # 设置为True启用测试模式
TEST_ROUNDS = 2          
PER_ROUND = 4           
# 测试模式配置

class ThreadSafeDF:
    def __init__(self, df):
        self.df = df
        self._lock = threading.Lock()
        self.column_count = len(df.columns)

    def update_row(self, index, values):
        with self._lock:
            # 数据对齐保障（在列过滤之后执行）
            adjusted = (values + ["无"] * self.column_count)[:self.column_count]
            self.df.loc[index] = adjusted

def process_row(index, columns, api_key):
    prompt = f"输出{index}的{','.join(columns)}，用大写字母S分隔，如果没有就回答'无'。按顺序列出结论即可，不必列出项目名称"
    
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": "你是一位刑法学分论老师"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        raw = response.choices[0].message.content
        result = raw.split("S")

        # 列名过滤机制
        column_set = set(columns)
        filtered_result = [item for item in result if item not in column_set]
        
        # 调试信息（测试模式时显示）
        if TEST_MODE and len(filtered_result) != len(result):
            removed = set(result) - set(filtered_result)
            print(f"[过滤日志] {index}: 移除了与列名重复的 {len(removed)} 项 → {removed}")

        # 长度验证
        if len(filtered_result) != len(columns):
            print(f"[异常] {index}: 预期{len(columns)}项，实际{len(filtered_result)}项")
            print(f"原始响应: {raw}")
        
        return (index, filtered_result)
    except Exception as e:
        print(f"[错误] {index}: {str(e)}")
        return (index, ["无"]*len(columns))

if __name__ == "__main__":
    origin_df = pd.read_excel('framework.xlsx')
    origin_df.set_index(origin_df.columns[0], inplace=True)
    ts_df = ThreadSafeDF(origin_df.copy())
    API_KEY = ""

    if TEST_MODE:
        print(f"[测试模式] 开始{TEST_ROUNDS}轮并发测试，每轮{PER_ROUND}次请求")
        total_test = TEST_ROUNDS * PER_ROUND
        test_indices = origin_df.index[:total_test]
        
        for round in range(TEST_ROUNDS):
            start = round * PER_ROUND
            end = start + PER_ROUND
            batch = test_indices[start:end]
            
            print(f"\n=== 第{round+1}轮测试 ===")
            with ThreadPoolExecutor(max_workers=32) as executor:
                futures = [executor.submit(process_row, idx, origin_df.columns.tolist(), API_KEY) for idx in batch]
                for future in futures:
                    idx, vals = future.result()
                    ts_df.update_row(idx, vals)
        
        ts_df.df.iloc[:total_test].to_excel('filter_test.xlsx', index=True)
        print(f"测试完成，过滤日志请查看控制台")
    
    else:
        with ThreadPoolExecutor(max_workers=32) as executor:
            futures = [executor.submit(process_row, idx, origin_df.columns.tolist(), API_KEY) for idx in origin_df.index]
            for future in futures:
                idx, vals = future.result()
                ts_df.update_row(idx, vals)
        
        ts_df.df.to_excel('final_output.xlsx', index=True)
