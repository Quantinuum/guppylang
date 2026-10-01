# from container_generated import dummy_action, make_container
# from guppylang import guppy


# @guppy
# def main() -> None:
#     value = make_container(42).consume()
#     dummy_action(value == 42, value)


# hugr = main.with_minimal_opt().compile()
# print(hugr.used_extensions().used_extensions)
# with open("demo.dot", "w") as dot_file:
#     dot_file.write(str(hugr.modules[0].render_dot()))
