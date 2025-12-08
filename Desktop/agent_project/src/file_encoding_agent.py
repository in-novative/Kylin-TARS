import chardet  # 自动识别编码的核心库

class FileEncodingAgent:
    """文件编码处理智能体：读取/转换/写入不同编码的文件"""
    def detect_encoding(self, file_path):
        """自动检测文件编码（返回编码+置信度）"""
        try:
            with open(file_path, "rb") as f:  # 二进制模式读取，避免编码干扰
                raw_data = f.read(2048)  # 读取前2048字节足够检测编码
                res = chardet.detect(raw_data)
                encoding = res["encoding"] or "utf-8"  # 兜底默认UTF-8
                confidence = round(res["confidence"], 2)
            return {
                "status": "success",
                "encoding": encoding,
                "confidence": confidence,
                "msg": f"检测到编码：{encoding}（置信度{confidence}）"
            }
        except Exception as e:
            return {"status": "error", "msg": f"检测失败：{str(e)}"}

    def read_file(self, file_path, encoding=None):
        """读取文件：指定编码/自动识别编码"""
        try:
            # 未指定编码则自动检测
            if not encoding:
                detect_res = self.detect_encoding(file_path)
                if detect_res["status"] != "success":
                    return detect_res
                encoding = detect_res["encoding"]
            # 读取文件（errors="replace"避免编码不匹配报错）
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                content = f.read()
            return {
                "status": "success",
                "content": content,
                "used_encoding": encoding,
                "msg": f"已用{encoding}编码读取文件"
            }
        except Exception as e:
            return {"status": "error", "msg": f"读取失败：{str(e)}"}

    def convert_encoding(self, src_path, dst_path, target_encoding="utf-8"):
        """转换文件编码（如GBK→UTF-8）"""
        try:
            # 先读取源文件（自动识别编码）
            read_res = self.read_file(src_path)
            if read_res["status"] != "success":
                return read_res
            # 写入新文件（指定目标编码）
            with open(dst_path, "w", encoding=target_encoding) as f:
                f.write(read_res["content"])
            return {
                "status": "success",
                "msg": f"编码转换完成：{read_res['used_encoding']} → {target_encoding}，文件保存至{dst_path}"
            }
        except Exception as e:
            return {"status": "error", "msg": f"转换失败：{str(e)}"}

# 测试代码（运行时自动执行）
if __name__ == "__main__":
    # 初始化智能体
    agent = FileEncodingAgent()
    
    # 1. 测试编码检测
    test_file = "/home/user1/Desktop/test_gbk.txt"
    detect_res = agent.detect_encoding(test_file)
    print("=== 编码检测结果 ===")
    print(detect_res)
    
    # 2. 测试读取文件
    read_res = agent.read_file(test_file)
    print("\n=== 文件读取结果 ===")
    print(f"内容：{read_res['content']}")
    print(f"使用编码：{read_res['used_encoding']}")
    
    # 3. 测试编码转换（GBK→UTF-8）
    dst_file = "/home/user1/Desktop/test_converted_utf8.txt"
    convert_res = agent.convert_encoding(test_file, dst_file, target_encoding="utf-8")
    print("\n=== 编码转换结果 ===")
    print(convert_res)
    
    # 4. 验证转换后的文件
    verify_res = agent.read_file(dst_file)
    print("\n=== 验证转换后文件 ===")
    print(f"内容：{verify_res['content']}")
    print(f"文件编码：{verify_res['used_encoding']}")




