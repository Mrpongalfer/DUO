# omnitide_cli/commands/exwork_cmds.py
import typer

app = typer.Typer(name="exwork", help="ExWork Agent Commands - NYI")


@app.command("run")
def exwork_run_cmd():
    typer.echo("ExWork run command placeholder")
