
package util
import("crypto/ed25519";"crypto/rand";"crypto/sha256";"encoding/hex";"encoding/json";"fmt";"os";"path/filepath";"time")
var JsonOut bool; var DryRun bool; var priv ed25519.PrivateKey; var pub ed25519.PublicKey
func init(){ p,s,_:=ed25519.GenerateKey(rand.Reader); pub=p; priv=s }
type Carrier struct{ Type string `json:"type"`; Time string `json:"time"`; Payload any `json:"payload"`; DryRun bool `json:"dryRun"`; Sig string `json:"sig"`; Pub string `json:"pub"` }
func marshalUnsigned(c Carrier) []byte { u:=Carrier{Type:c.Type,Time:c.Time,Payload:c.Payload,DryRun:c.DryRun}; b,_:=json.Marshal(u); return b }
func Emit(kind string, payload any){
  c := Carrier{ Type:kind, Time: time.Now().UTC().Format(time.RFC3339), Payload:payload, DryRun:DryRun }
  h := sha256.Sum256(marshalUnsigned(c))
  c.Sig = hex.EncodeToString(ed25519.Sign(priv, h[:])); c.Pub = hex.EncodeToString(pub)
  b,_ := json.Marshal(c)
  if JsonOut { fmt.Println(string(b)) } else { fmt.Printf("%s: %s\n", kind, string(b)) }
  os.MkdirAll("out/carriers",0o755); os.WriteFile(filepath.Join("out/carriers", fmt.Sprintf("%d.json", time.Now().UnixNano())), b, 0o644)
}
