package cmd
import("os";"github.com/spf13/cobra";"github.com/socioprophet/prophet/internal/util")
var rootCmd=&cobra.Command{Use:"prophet"}
func init(){rootCmd.PersistentFlags().BoolVar(&util.JsonOut,"json",false,"JSON");rootCmd.PersistentFlags().BoolVar(&util.DryRun,"dry-run",false,"dry-run");rootCmd.AddCommand(A2ACmd())}
func Execute(){ if err:=rootCmd.Execute(); err!=nil { os.Exit(1) } }
