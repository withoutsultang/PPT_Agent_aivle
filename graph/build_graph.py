from langgraph.graph import StateGraph, END
from nodes.node_parse_ppt import node_parse_ppt
from nodes.node_generate_text import node_generate_text
from nodes.node_generate_script import node_generate_script
from nodes.node_tts import node_tts
from nodes.node_make_video import node_make_video

def build_agent_graph(State):
    builder = StateGraph(State)
    builder.add_node('parse_ppt', node_parse_ppt)
    builder.add_node('generate_page', node_generate_text)
    builder.add_node('generate_script', node_generate_script)
    builder.add_node('tts_mp3', node_tts)
    builder.add_node('make_video', node_make_video)

    builder.set_entry_point('parse_ppt')
    builder.add_edge('parse_ppt', 'generate_page')
    builder.add_edge('generate_page', 'generate_script')
    builder.add_edge('generate_script', 'tts_mp3')
    builder.add_edge('tts_mp3', 'make_video')
    builder.set_finish_point('make_video')
    return builder.compile()
