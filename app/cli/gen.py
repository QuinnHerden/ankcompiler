import typer

from app.logic.drivers import generate_chunk

gen_app = typer.Typer()


@gen_app.command("chunk")
def gen_chunk() -> None:
    """Generates an empty note chunk."""

    note_chunk = generate_chunk()

    typer.echo(note_chunk)
