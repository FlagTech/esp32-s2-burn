import esptool
import serial.tools.list_ports
import os
import subprocess
import sys

def get_ports(pid):
    """列出所有可用的序列埠"""
    ports = serial.tools.list_ports.comports()

    ports = [
        port.device for port in ports 
        if port.vid == 12346 and port.pid == pid
    ]
    return ports


def find_test_files(directory=None):
    """
    檢查指定資料夾下是否有 test 開頭的 .py 檔案
    如果未指定資料夾，則檢查目前的工作資料夾
    
    返回：test 開頭的 .py 檔案清單
    """
    # 如果未指定資料夾，使用目前的工作資料夾
    if directory is None:
        directory = os.getcwd()
        
    test_files = []
    
    # 列出目前資料夾下的所有檔案
    try:
        for filename in os.listdir(directory):
            # 檢查是否為檔案，且檔名是否以 test 開頭，副檔名是否為 .py
            if (os.path.isfile(os.path.join(directory, filename)) and 
                filename.startswith('test') and 
                filename.endswith('.py')):
                test_files.append(filename)
                
        return test_files
        
    except Exception as e:
        print(f"檢查檔案時發生錯誤：{str(e)}")
        return []


def write_flash(selected_port, firmware_path):
    ret = esptool.main(
        [
            "--chip", "esp32s2",
            "--port", selected_port,
            "--baud", "460800",
            "--after", "no_reset",
            "write_flash",
            "--erase-all",
            "0x1000",
            firmware_path
        ]
    )
    print(ret)


def port_exists(port):
    while True:
        ports = get_ports(2) # s2 燒錄模式下的 pid
        if port in ports:
            break
        if ports:
            print(f'找到其他連接埠：{', '.join(ports)}')
        print(f'找不到指定的連接埠：{port}')
        print('請按板子右側的 0 不要放，再按一下左側的 RST 一下後放開')
        ans = input('請按 Enter 繼續（按 q 退出）：')
        if ans.lower() == 'q':
            return False
    print(f'找到連接埠：{port}')
    return True


def get_cdc_port():
    cdc_ports = []
    while not cdc_ports:
        before = get_ports(16385) # s2 正常工作模式下的 pid
        ans = input('請按一下板子左側的 RST 小按鈕後按 Enter 繼續，輸入 q 退出: ')
        if ans == 'q': 
            print("程式已退出")
            return None

        after = get_ports(16385) # s2 正常工作模式下的 pid
        cdc_ports = after.remove(before) if before else after # 移除之前的連接埠
            
        if cdc_ports:
            print(f'找到新的 CDC 埠: {cdc_ports}')
            return cdc_ports[0]
        else:
            print("未檢測到新的 CDC 埠，請再試一次")

def run_tests(cdc_port):
    for file in find_test_files('./test'):
        print(f'執行測試檔案: {file}')
        process = subprocess.Popen(
            ['uv', 'run', 'ampy', '-p', cdc_port, 'run', f'./test/{file}'], 
            shell=True,             # 在 shell 中執行
            stdout=subprocess.PIPE, # 擷取標準輸出
            stderr=subprocess.PIPE, # 擷取錯誤輸出
        )
        
        # 即時讀取輸出
        test_ok = False
        while True:
            output = process.stdout.readline().decode('utf-8').strip()
            if output == '' and process.poll() is not None:
                break
            print(output)
            # 如果沒有輸出且行程結束
            if '**OK**' in output:
                test_ok = True
        
        error = process.stderr.read().decode('utf-8').strip()
        if error:
            print(f'發生錯誤：{error}')

        process.wait()

        if test_ok:
            print(f'測試檔案 {file} 執行成功')
        else:
            print(f'測試檔案 {file} 執行失敗')
            return False
    return True
        
def main():

    if len(sys.argv) < 3:
        print("用法: python main.py <firmware_path> <port>")
        print("範例: python main.py firmware.bin COM3")
        return
    firmware_path = sys.argv[1]
    selected_port = sys.argv[2].upper()

    ans = ''
    while True:
        if not port_exists(selected_port):
            return
        
        write_flash(selected_port, firmware_path)
    
        cdc_port = get_cdc_port()
        if not cdc_port:
            return
        
        if not run_tests(cdc_port):
            print("測試未通過，請檢查連接埠")          
        ans = input('燒錄完成，請按 Enter 繼續（按 q 退出）：')
        if ans.lower() == 'q':
            print("程式已退出")
            return


if __name__ == "__main__":
    main()
