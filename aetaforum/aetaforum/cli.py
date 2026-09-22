import typer
import subprocess
import os
import sys

app = typer.Typer()

@app.callback(invoke_without_command=True)
def cli(ctx: typer.Context):
    """
    Launch the aetaforum Rust/Tauri application.
    """
    if ctx.invoked_subcommand is None:
        # Find the bundled exe
        base_dir = os.path.dirname(os.path.abspath(__file__))
        bin_dir = os.path.join(base_dir, "bin")
        
        # Determine OS and executable name
        exe_name = "app.exe" if sys.platform.startswith("win") else "app"
        exe_path = os.path.join(bin_dir, exe_name)
        
        if not os.path.exists(exe_path):
            print(f"Error: Rust binary not found at {exe_path}", file=sys.stderr)
            print("Please ensure the package was built correctly with the Tauri binary included.", file=sys.stderr)
            sys.exit(1)
            
        # Pass the current working directory as an argument if needed, or set CWD
        cwd = os.getcwd()
        print(f"Starting Aetaforum from {cwd}...")
        
        try:
            # We use Popen and wait to keep the CLI blocked while the app runs
            process = subprocess.Popen([exe_path], cwd=cwd)
            process.wait()
        except KeyboardInterrupt:
            process.terminate()
            process.wait()

def main():
    app()

if __name__ == "__main__":
    main()
