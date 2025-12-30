
package cmd
import("fmt";"github.com/spf13/cobra";"github.com/socioprophet/prophet/internal/mcp";"github.com/socioprophet/prophet/internal/util")
func A2ACmd()*cobra.Command{
  var repo,ticket,cfgPath string; var live bool
  c:=&cobra.Command{Use:"a2a run", RunE: func(_ *cobra.Command,_ []string) error{
    if repo=="" { return fmt.Errorf("--repo required") }
    if cfgPath=="" { cfgPath=".mcp/servers.json" }
    util.DryRun=!live; cfg,err:=mcp.LoadConfig(cfgPath); if err!=nil { return err }
    fs,_ := mcp.Find(cfg,"filesystem"); ts,_ := mcp.Find(cfg,"tests"); sc,_ := mcp.Find(cfg,"scmhost"); df,_ := mcp.Find(cfg,"diff")
    util.Emit("a2a.author.propose", map[string]any{"repo":repo,"ticket":ticket})
    if live{ _,_ = mcp.Call(fs.Socket, mcp.Header{Mode:"B2",SchemaId:"caps.fs.v1",ContextId:"ctx:fs",Tool:"filesystem",Method:"write"}, []byte(`{"path":"examples/demo_ticket.md","content":"- [x] `+ticket+`\n"}`)) }
    util.Emit("a2a.author.test", map[string]any{"suite":"quick"}); if live{ _,_ = mcp.Call(ts.Socket, mcp.Header{Mode:"B2",SchemaId:"caps.tests.v1",ContextId:"ctx:tests",Tool:"tests",Method:"run"}, []byte(`{"suite":"quick"}`)) }
    util.Emit("a2a.author.pr.open", map[string]any{"title":"feat: "+ticket}); if live{ _,_ = mcp.Call(sc.Socket, mcp.Header{Mode:"B2",SchemaId:"caps.scm.v1",ContextId:"ctx:scm",Tool:"scmhost",Method:"open_pr"}, []byte(`{"title":"feat: `+ticket+`","base":"main","head":"feat/`+ticket+`"}`)) }
    util.Emit("a2a.reviewer.block", map[string]any{"reason":"nit"}); if live{ _,_ = mcp.Call(df.Socket, mcp.Header{Mode:"B2",SchemaId:"caps.diff.v1",ContextId:"ctx:diff",Tool:"diff",Method:"annotate"}, []byte(`{"comment":"nit: add newline"}`)) }
    util.Emit("a2a.author.revise", map[string]any{"action":"append newline"}); if live{ _,_ = mcp.Call(fs.Socket, mcp.Header{Mode:"B2",SchemaId:"caps.fs.v1",ContextId:"ctx:fs",Tool:"filesystem",Method:"write"}, []byte(`{"path":"examples/demo_ticket.md","content":"- [x] `+ticket+`\n\n"}`)) }
    util.Emit("a2a.arbiter.merge", map[string]any{"method":"squash"}); if live{ _,_ = mcp.Call(sc.Socket, mcp.Header{Mode:"B2",SchemaId:"caps.scm.v1",ContextId:"ctx:scm",Tool:"scmhost",Method:"merge_pr"}, []byte(`{"method":"squash"}`)) }
    util.Emit("a2a.done", map[string]any{"repo":repo,"ticket":ticket,"live":live}); return nil
  }}
  c.Flags().StringVar(&repo,"repo","", "owner/repo"); c.Flags().StringVar(&ticket,"ticket","DEMO","ticket id")
  c.Flags().StringVar(&cfgPath,"mcp",".mcp/servers.json","MCP config path"); c.Flags().BoolVar(&live,"live",false,"live mode")
  return c
}
