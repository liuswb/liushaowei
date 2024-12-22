import socket

def test_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    
    try:
        # 尝试绑定所有网络接口
        sock.bind(('0.0.0.0', port))
        print(f"Port {port} is available")
        return True
    except socket.error as e:
        print(f"Port {port} is in use or not available: {e}")
        return False
    finally:
        sock.close()

if __name__ == '__main__':
    # 测试 5000 端口
    test_port(5000)
    
    # 打印本机所有 IP 地址
    hostname = socket.gethostname()
    print(f"\nHostname: {hostname}")
    print("\nAvailable IP addresses:")
    for ip in socket.gethostbyname_ex(hostname)[2]:
        print(f"- {ip}") 