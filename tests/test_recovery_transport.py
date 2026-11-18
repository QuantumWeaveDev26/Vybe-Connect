"""Real SMTP/TLS delivery into a local capture server; no external mail is sent."""
import datetime,ipaddress,os,socket,ssl,tempfile,threading,unittest
from pathlib import Path
from email import policy
from email.parser import BytesParser
from unittest.mock import patch
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from recovery_mail import send_recovery

class RecoveryTransportTests(unittest.TestCase):
    def test_recovery_message_reaches_a_certificate_verified_local_smtp_server(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
            name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')]);now=datetime.datetime.now(datetime.timezone.utc)
            cert=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1)).not_valid_after(now+datetime.timedelta(hours=1)).add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False).sign(key,hashes.SHA256())
            cert_path=root/'cert.pem';key_path=root/'key.pem';cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM));key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(cert_path,key_path)
            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(5);port=listener.getsockname()[1]
            captured=[];errors=[]
            def serve():
                try:
                    with listener.accept()[0] as raw,tls.wrap_socket(raw,server_side=True) as connection,connection.makefile('rwb',buffering=0) as stream:
                        connection.settimeout(5);stream.write(b'220 local capture\r\n')
                        while True:
                            line=stream.readline(65536)
                            if not line:break
                            command=line.split(b' ',1)[0].strip().upper()
                            if command in (b'EHLO',b'HELO'):stream.write(b'250-localhost\r\n250 SIZE 65536\r\n')
                            elif command in (b'MAIL',b'RCPT',b'RSET'):stream.write(b'250 OK\r\n')
                            elif command==b'DATA':
                                stream.write(b'354 End with dot\r\n');body=[]
                                while True:
                                    part=stream.readline(65536)
                                    if part==b'.\r\n':break
                                    if not part:raise OSError('Incomplete SMTP body')
                                    body.append(part[1:] if part.startswith(b'..') else part)
                                captured.append(b''.join(body));stream.write(b'250 Captured\r\n')
                            elif command==b'QUIT':stream.write(b'221 Bye\r\n');break
                            else:raise OSError('Unexpected SMTP command')
                except Exception as error:errors.append(type(error).__name__)
                finally:listener.close()
            worker=threading.Thread(target=serve,daemon=True);worker.start()
            client=ssl.create_default_context(cafile=str(cert_path))
            env={'TW_RECOVERY_ENABLED':'true','TW_RECOVERY_SECRET':'x'*40,'TW_PUBLIC_ORIGIN':'https://vybe.example','TW_SMTP_HOST':'127.0.0.1','TW_SMTP_PORT':str(port),'TW_SMTP_SECURITY':'ssl','TW_SMTP_FROM':'recovery@vybe.example'}
            try:
                with patch.dict(os.environ,env,clear=True),patch('recovery_mail.ssl.create_default_context',return_value=client):send_recovery('owner@example.test','https://vybe.example/#reset=synthetic-token')
            finally:worker.join(6);listener.close()
            self.assertFalse(worker.is_alive());self.assertEqual(errors,[]);self.assertEqual(len(captured),1)
            message=BytesParser(policy=policy.default).parsebytes(captured[0]);self.assertEqual(message['To'],'owner@example.test');self.assertTrue(message['Message-ID']);self.assertIn('synthetic-token',message.get_content());self.assertTrue(client.check_hostname)
