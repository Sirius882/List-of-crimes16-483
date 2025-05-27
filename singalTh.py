import pandas as pd
from openai import OpenAI

df = pd.read_excel('framework.xlsx')
df = df.set_index(df.columns[0])

j = 0
for i in df.index:
    prompt = "输出" + i + "的" + ','.join(df.columns) + "，用大写字母L分隔，如果没有就回答“无”。按顺序列出结论即可，不必列出项目名称。"

    client = OpenAI(api_key="", base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[
            {"role": "system", "content": "你是一位刑法学分论老师"},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    answer = response.choices[0].message.content.split('L')
    df.loc[i] = answer
    
    # j += 1
    # if j >= 1:
    #     break

df.to_excel('output.xlsx', index=True)