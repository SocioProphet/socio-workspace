package main

import (
	"encoding/json"
	"image/color"
	"image"
	"image/draw"
	"image/png"
	"io"
	"log"
	"net/http"
	"os"
	"path"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

type Spec struct {
	ID        string                 `json:"id"`
	Name      string                 `json:"name,omitempty"`
	CreatedAt time.Time              `json:"created_at"`
	Meta      map[string]interface{} `json:"meta,omitempty"`
}
var specs = map[string]Spec{}
var data = map[string][]byte{}

func ok(w http.ResponseWriter, v any){ w.Header().Set("Content-Type","application/json"); _=json.NewEncoder(w).Encode(v) }
func unauthorized(w http.ResponseWriter){ w.WriteHeader(http.StatusUnauthorized); ok(w,map[string]any{"ok":false,"error":"unauthorized"}) }

func auth(r *http.Request) bool {
	t := os.Getenv("DEV_TOKEN")
	k := os.Getenv("API_KEY")
	if t=="" && k=="" { return true }
	if strings.HasPrefix(r.Header.Get("Authorization"), "Bearer ") && strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer ")==t { return true }
	if r.Header.Get("X-API-Key")==k && k!="" { return true }
	return false
}

func specsHandler(w http.ResponseWriter, r *http.Request){
	if !auth(r){ unauthorized(w); return }
	switch r.Method{
	case "GET":
		arr := make([]Spec,0,len(specs))
		for _,s := range specs { arr = append(arr,s) }
		ok(w,map[string]any{"ok":true,"items":arr})
	case "POST":
		var in Spec
		_ = json.NewDecoder(r.Body).Decode(&in)
		if in.ID==""{ in.ID = time.Now().UTC().Format("20060102T150405.000Z") }
		in.CreatedAt = time.Now().UTC()
		specs[in.ID]=in
		ok(w,map[string]any{"ok":true,"item":in})
	case "DELETE":
		base := strings.TrimSuffix(r.URL.Path,"/")
		if path.Base(base) != "specs" {
			delete(specs, path.Base(base))
			ok(w,map[string]any{"ok":true,"deleted":path.Base(base)})
			return
		}
		specs = map[string]Spec{}
		ok(w,map[string]any{"ok":true,"deleted_all":true})
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}
func specByID(w http.ResponseWriter, r *http.Request){
	if !auth(r){ unauthorized(w); return }
	parts := strings.Split(strings.Trim(r.URL.Path,"/"),"/")
	if len(parts)<3 { w.WriteHeader(http.StatusBadRequest); ok(w,map[string]any{"ok":false,"error":"missing id"}); return }
	id := parts[2]
	sp,okk := specs[id]
	if !okk{ w.WriteHeader(http.StatusNotFound); ok(w,map[string]any{"ok":false,"error":"not found"}); return }
	ok(w,map[string]any{"ok":true,"item":sp})
}
func dataHandler(w http.ResponseWriter, r *http.Request){
	if !auth(r){ unauthorized(w); return }
	parts := strings.Split(strings.Trim(r.URL.Path,"/"),"/")
	if len(parts)<3 { w.WriteHeader(http.StatusBadRequest); ok(w,map[string]any{"ok":false,"error":"missing id"}); return }
	id := parts[2]
	switch r.Method{
	case "GET":
		if b,okk := data[id]; okk { w.Header().Set("Content-Type","application/json"); w.Write(b); return }
		ok(w,map[string]any{"ok":true,"data":nil})
	case "POST":
		b, _ := io.ReadAll(r.Body)
		data[id]=b
		ok(w,map[string]any{"ok":true})
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}
func imageHandler(w http.ResponseWriter, r *http.Request){
	if !auth(r){ unauthorized(w); return }
	base := path.Base(r.URL.Path)
	if strings.HasSuffix(base,".png"){
		w.Header().Set("Content-Type","image/png")
		img := image.NewRGBA(image.Rect(0,0,320,160))
		draw.Draw(img,img.Bounds(),&image.Uniform{color.RGBA{220,235,255,255}},image.Point{},draw.Src)
		_ = png.Encode(w,img); return
	}
	if strings.HasSuffix(base,".svg"){
		w.Header().Set("Content-Type","image/svg+xml")
		w.Write([]byte(`<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="320" height="160"><rect x="0" y="0" width="320" height="160" fill="#e6f0ff"/><circle cx="80" cy="80" r="30" fill="#bcd2ff"/><text x="130" y="88" font-family="sans-serif" font-size="20" fill="#1f2937">SocioProphet</text></svg>`)); return
	}
	w.WriteHeader(http.StatusNotFound)
}

var upgrader = websocket.Upgrader{ CheckOrigin: func(r *http.Request) bool { return true } }
func wsHandler(w http.ResponseWriter, r *http.Request){
	if !auth(r){ w.WriteHeader(http.StatusUnauthorized); return }
	c,err := upgrader.Upgrade(w,r,nil); if err!=nil { return }; defer c.Close()
	type evt struct{ Type,SpecID,Phase,Msg string; Progress float64 `json:"progress,omitempty"` }
	specID := r.URL.Query().Get("spec"); if specID==""{ specID="unknown" }
	c.WriteJSON(evt{Type:"hello",SpecID:specID,Msg:"connected"})
	for i:=0;i<=10;i++{ time.Sleep(200*time.Millisecond); c.WriteJSON(evt{Type:"progress",SpecID:specID,Phase:"eval",Progress:float64(i)/10.0}) }
	c.WriteJSON(evt{Type:"done",SpecID:specID,Msg:"complete"})
}

func health(w http.ResponseWriter, r *http.Request){ ok(w,map[string]any{"ok":true,"time":time.Now().UTC().Format(time.RFC3339Nano)}) }

func main(){
	mux := http.NewServeMux()
	mux.HandleFunc("/api/specs", specsHandler)
	mux.HandleFunc("/api/specs/", specByID)
	mux.HandleFunc("/api/data/", dataHandler)
	mux.HandleFunc("/api/image/", imageHandler)
	mux.HandleFunc("/ws", wsHandler)
	mux.HandleFunc("/health", health)
	port := os.Getenv("PORT"); if port==""{ port="5175" }
	log.Printf("dev-api wiring server :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, mux))
}
