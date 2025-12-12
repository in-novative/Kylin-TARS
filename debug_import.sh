#!/bin/bash
echo "=== Python导入问题诊断 ==="

# 检查utils模块位置
echo "1. 查找utils目录:"
find /data1/jjc/Kylin-TARS -name "utils" -type d 2>/dev/null

echo -e "\n2. 检查目标utils目录:"
utils_path="/data1/jjc/Kylin-TARS/desktop/agent_project/src/utils"
if [ -d "$utils_path" ]; then
    echo "✓ utils目录存在: $utils_path"
    ls -la "$utils_path"
    
    echo -e "\n3. 检查__init__.py:"
    if [ -f "$utils_path/__init__.py" ]; then
        echo "✓ __init__.py存在"
    else
        echo "✗ __init__.py不存在，需要创建"
        echo "创建 __init__.py..."
        touch "$utils_path/__init__.py"
    fi
else
    echo "✗ utils目录不存在: $utils_path"
fi

echo -e "\n4. PYTHONPATH检查:"
echo "PYTHONPATH=$PYTHONPATH"

echo -e "\n5. Python路径检查:"
python -c "
import sys
import os
print('Python版本:', sys.version)
print('当前工作目录:', os.getcwd())
print('\nPython搜索路径:')
for i, path in enumerate(sys.path):
    print(f'{i}: {path}')
"

echo -e "\n6. 测试导入:"
python -c "
import sys
import os
sys.path.insert(0, '/data1/jjc/Kylin-TARS/desktop/agent_project/src')
try:
    from utils.set_logger import set_logger
    print('✓ 导入成功!')
except ImportError as e:
    print(f'✗ 导入失败: {e}')
"
