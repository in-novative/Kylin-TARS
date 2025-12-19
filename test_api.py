from openai import OpenAI

# client = OpenAI(
#   base_url="https://openrouter.ai/api/v1",
#   api_key="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",
# )

# completion = client.chat.completions.create(
# #   extra_headers={
# #     "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
# #     "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
# #   },
#   model="qwen/qwen2.5-vl-32b-instruct:free",
#   messages=[
#     {
#       "role": "user",
#       "content": "你是Qwen2.5 VL吗？"
#     }
#   ]
# )

# print(completion.choices[0].message.content)

# client2 = OpenAI(
#   base_url="https://openrouter.ai/api/v1",
#   api_key="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",
# )

# completion = client2.chat.completions.create(
# #   extra_headers={
# #     "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
# #     "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
# #   },
#   model="meta-llama/llama-3.3-70b-instruct:free",
#   messages=[
#     {
#       "role": "user",
#       "content": "你是哪一个模型？你的参数量有多大？"
#     }
#   ]
# )

# print(completion.choices[0].message.content)

client = OpenAI(
  base_url="https://xiaoai.plus/v1",
  api_key="sk-lgW2a38mNKdL3lAfKnjQ55yl3NujlfAwlg7u6GqjOfJXyOKU",
)

completion = client.chat.completions.create(
#   extra_headers={
#     "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
#     "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
#   },
  model="gpt-4o-mini",
  messages=[
    {
      "role": "user",
      "content": "你是哪一家公司开发的哪一款模型"
    }
  ]
)

print(completion.choices[0].message.content)
