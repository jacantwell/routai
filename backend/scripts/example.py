import logging
from typing import Any, Dict
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from app.agent.graph.workflow import app, create_route_planner_graph
from app.config.logging import setup_logging
from app.models.state import AgentState

# Setup logging for examples
setup_logging(level="INFO")
logger = logging.getLogger(__name__)


def example_basic_usage():
    """Basic single-turn conversation example."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Basic Usage")
    print("=" * 60 + "\n")

    config = RunnableConfig(configurable={"thread_id": "example-1"})

    user_message = "I want to bike from London to Paris, covering about 80km per day"

    print(f"User: {user_message}\n")

    # Invoke the graph
    result = app.invoke({"messages": [HumanMessage(content=user_message)]}, config)

    # Get the last message
    last_message = result["messages"][-1]
    print(f"Assistant: {last_message.content}\n")


def example_streaming():
    """Example using streaming for real-time responses."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Streaming Responses")
    print("=" * 60 + "\n")

    config = {"configurable": {"thread_id": "example-2"}}

    user_message = "Plan a bikepacking route from Berlin to Amsterdam"
    print(f"User: {user_message}\n")
    print("Assistant: ", end="", flush=True)

    # Stream the conversation
    for event in app.stream(
        {"messages": [HumanMessage(content=user_message)]}, config, stream_mode="values"
    ):
        # Get the last message from the event
        if event.get("messages"):
            last_message = event["messages"][-1]
            # Only print AI messages
            if hasattr(last_message, "content") and last_message.content:
                if last_message.type == "ai":
                    print(last_message.content, end="\n\n", flush=True)


def example_multi_turn():
    """Example of a multi-turn conversation with state persistence."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Multi-turn Conversation")
    print("=" * 60 + "\n")

    # Use the same thread_id for conversation continuity
    config = {"configurable": {"thread_id": "example-3"}}

    # Turn 1
    print("User: I'm planning a bike trip from Edinburgh to London\n")
    result = app.invoke(
        {
            "messages": [
                HumanMessage(
                    content="I'm planning a bike trip from Edinburgh to London"
                )
            ]
        },
        config,
    )
    print(f"Assistant: {result['messages'][-1].content}\n")

    # Turn 2
    print("User: I want to do about 100km per day\n")
    result = app.invoke(
        {"messages": [HumanMessage(content="I want to do about 100km per day")]}, config
    )
    print(f"Assistant: {result['messages'][-1].content}\n")


def example_state_inspection():
    """Example showing how to inspect state at different stages."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: State Inspection")
    print("=" * 60 + "\n")

    config = {"configurable": {"thread_id": "example-4"}}

    # Use a complete request
    user_message = "Create a route from Barcelona to Madrid, 120km daily"

    print(f"User: {user_message}\n")
    print("Processing stages:")

    for i, event in enumerate(
        app.stream(
            {"messages": [HumanMessage(content=user_message)]},
            config,
            stream_mode="values",
        ),
        1,
    ):
        state = event

        # Check what data is available at each step
        if state.get("requirements"):
            print(f"\n  [{i}] Requirements gathered:")
            req = state["requirements"]
            print(f"      Origin: {req.origin.name}")
            print(f"      Destination: {req.destination.name}")
            print(f"      Daily distance: {req.daily_distance_km}km")

        if state.get("route") and not state.get("waypoints"):
            print(f"\n  [{i}] Route calculated:")
            route = state["route"]
            print(f"      Total distance: {route.distance / 1000:.2f}km")

        if state.get("waypoints"):
            print(f"\n  [{i}] Waypoints generated:")
            print(f"      Number of days: {len(state['waypoints'])}")

        # Check for final message
        if state.get("messages"):
            last_msg = state["messages"][-1]
            if last_msg.type == "ai" and "itinerary" in last_msg.content.lower():
                print(f"\n  [{i}] Itinerary created ✓")


def example_error_handling():
    """Example showing error handling."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Error Handling")
    print("=" * 60 + "\n")

    config = {"configurable": {"thread_id": "example-5"}}

    try:
        # This should work fine
        print("Test 1: Valid request")
        result = app.invoke(
            {"messages": [HumanMessage(content="Rome to Florence, 70km/day")]}, config
        )
        print("✓ Success\n")

    except Exception as e:
        print(f"✗ Error: {str(e)}\n")

    try:
        # This might cause issues if locations can't be found
        print("Test 2: Invalid location")
        result = app.invoke(
            {"messages": [HumanMessage(content="XYZ123 to ABC456, 100km/day")]}, config
        )
        print("✓ Success (or gracefully handled)\n")

    except Exception as e:
        print(f"✗ Error: {str(e)}\n")


def example_custom_configuration():
    """Example using custom LLM configuration."""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Custom Configuration")
    print("=" * 60 + "\n")

    # Create a custom graph with different settings
    # Note: You would need to modify the create_route_planner_graph
    # function to accept custom LLM settings, or manually rebuild the graph

    print("Creating custom graph with Sonnet model...")

    # For now, we'll just use the default
    # In production, you'd pass custom settings to create_route_planner_graph()
    custom_app = create_route_planner_graph()

    config = {"configurable": {"thread_id": "example-6"}}

    result = custom_app.invoke(
        {"messages": [HumanMessage(content="Prague to Vienna, 90km daily")]}, config
    )

    print(f"Response: {result['messages'][-1].content[:200]}...\n")


def example_conversation_history():
    """Example accessing conversation history."""
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Conversation History")
    print("=" * 60 + "\n")

    config = {"configurable": {"thread_id": "example-7"}}

    # Have a short conversation
    messages = [
        "I want to plan a trip from Lyon to Nice",
        "80km per day please",
    ]

    for msg in messages:
        print(f"User: {msg}")
        result = app.invoke({"messages": [HumanMessage(content=msg)]}, config)
        print(f"Assistant: {result['messages'][-1].content[:100]}...\n")

    # Access the full conversation history
    state = app.get_state(config)
    print(f"Total messages in conversation: {len(state.values.get('messages', []))}")
    print("\nFull conversation:")
    for i, msg in enumerate(state.values.get("messages", []), 1):
        role = "User" if msg.type == "human" else "Assistant"
        content = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        print(f"  {i}. {role}: {content}")


def example_batch_planning():
    """Example planning multiple routes in batch."""
    print("\n" + "=" * 60)
    print("EXAMPLE 8: Batch Planning")
    print("=" * 60 + "\n")

    routes = [
        ("route-1", "Amsterdam to Brussels, 75km/day"),
        ("route-2", "Copenhagen to Malmo, 60km/day"),
        ("route-3", "Oslo to Bergen, 100km/day"),
    ]

    print(f"Planning {len(routes)} routes...\n")

    for route_id, request in routes:
        config = {"configurable": {"thread_id": route_id}}

        try:
            result = app.invoke({"messages": [HumanMessage(content=request)]}, config)
            status = "✓" if result.get("waypoints") else "..."
            print(f"{status} {route_id}: {request}")

        except Exception as e:
            print(f"✗ {route_id}: Error - {str(e)}")


def run_all_examples():
    """Run all examples in sequence."""
    examples = [
        example_basic_usage,
        example_streaming,
        example_multi_turn,
        example_state_inspection,
        example_error_handling,
        example_custom_configuration,
        example_conversation_history,
        example_batch_planning,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            logger.error(f"Example failed: {example_func.__name__}", exc_info=True)
            print(f"\n✗ Example failed: {str(e)}\n")

        input("Press Enter to continue to next example...")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("BIKEPACKING ROUTE PLANNER - USAGE EXAMPLES")
    print("=" * 60)

    print("\nAvailable examples:")
    print("1. Basic Usage")
    print("2. Streaming Responses")
    print("3. Multi-turn Conversation")
    print("4. State Inspection")
    print("5. Error Handling")
    print("6. Custom Configuration")
    print("7. Conversation History")
    print("8. Batch Planning")
    print("9. Run all examples")

    choice = input("\nSelect example (1-9): ").strip()

    examples = {
        "1": example_basic_usage,
        "2": example_streaming,
        "3": example_multi_turn,
        "4": example_state_inspection,
        "5": example_error_handling,
        "6": example_custom_configuration,
        "7": example_conversation_history,
        "8": example_batch_planning,
        "9": run_all_examples,
    }

    if choice in examples:
        examples[choice]()
    else:
        print("Invalid choice")
