
package mcp
import("crypto/hkdf";"encoding/binary";"encoding/json";"errors";"io";"net";"os";"sync";"golang.org/x/crypto/sha3";"golang.org/x/crypto/chacha20poly1305";"github.com/socioprophet/prophet/internal/util")
type Server struct{ ID, Socket, Schema string }
type Config struct{ Servers []Server `json:"servers"` }
type Header struct{ Mode,SchemaId,ContextId,Tool,Method string; Nonce uint64 }
func LoadConfig(path string)(Config,error){ b,err:=os.ReadFile(path); if err!=nil { return Config{},err }; var c Config; return c,json.Unmarshal(b,&c) }
func Find(c Config, id string)(Server,bool){ for _,s:= range c.Servers{ if s.ID==id {return s,true} } ; return Server{},false }
func deriveKey(hb []byte)([]byte,error){ hk:=hkdf.New(sha3.New256(), make([]byte,32), hb, []byte("TritRPC-HKDF")); key:=make([]byte, chacha20poly1305.KeySize); _,err:=io.ReadFull(hk,key); return key,err }
var nonceMu sync.Mutex; var lastNonce=map[string]uint64{}
func nextNonce(tool string) uint64{ nonceMu.Lock(); defer nonceMu.Unlock(); lastNonce[tool]++; return lastNonce[tool] }
func Call(sock string, hdr Header, payload []byte)([]byte,error){
  if hdr.Nonce==0{ hdr.Nonce = nextNonce(hdr.Tool) }
  hb,_ := json.Marshal(hdr)
  crc := util.CRC16CCITT(payload); body := append(payload, byte(crc>>8), byte(crc&0xff))
  key,err:=deriveKey(hb); if err!=nil { return nil, err }
  aead,_ := chacha20poly1305.New(key); nonce := make([]byte, aead.NonceSize())
  ct := aead.Seal(nil, nonce, body, hb)
  conn,err := net.Dial("unix", sock); if err!=nil { return nil, err }; defer conn.Close()
  var l [8]byte; binary.BigEndian.PutUint32(l[:4], uint32(len(hb))); binary.BigEndian.PutUint32(l[4:], uint32(len(ct)))
  conn.Write(l[:]); conn.Write(hb); conn.Write(ct)
  io.ReadFull(conn, l[:]); hl:=int(binary.BigEndian.Uint32(l[:4])); bl:=int(binary.BigEndian.Uint32(l[4:]))
  rh:=make([]byte,hl); io.ReadFull(conn,rh); rc:=make([]byte,bl); io.ReadFull(conn,rc)
  rkey,_ := deriveKey(rh); raead,_ := chacha20poly1305.New(rkey); plain,err := raead.Open(nil, nonce, rc, rh); if err!=nil { return nil, err }
  if len(plain)<2 { return nil, errors.New("short body") }
  return plain[:len(plain)-2], nil
}
