"""
Memory Intelligence Examples — Phase 2.3

Demonstrates:
  1. Learning from repeated executions
  2. Pattern extraction and discovery
  3. Prediction of next actions
  4. Plan optimization based on history
  5. Feedback and reinforcement
  6. Proactive recommendations
"""
from __future__ import annotations

import asyncio

from app.memory.learning_system import get_learning_system
from app.memory.models import ExecutionTrace, LearningFeedback
from app.orchestration.ehsa_enhanced import EnhancedEHSA
from app.orchestration.tool_builders import register_analytics_tools


# =============================================================================
# Example 1: Learning From Repeated Executions
# =============================================================================


async def example_learning_pattern():
    """
    User repeats the same workflow multiple times.
    System learns the pattern.
    """
    print("\n[Example 1] Learning From Repeated Executions")
    print("-" * 80)

    learning_system = get_learning_system()
    user_id = "user_example_1"

    # Simulate 5 repeated executions: analyzer → reporter
    for i in range(5):
        trace = ExecutionTrace(
            execution_id=f"exec_{i}",
            user_id=user_id,
            goal="Analyze and report",
            steps=[
                {"tool_id": "analytics.analyze", "status": "success"},
                {"tool_id": "analytics.report", "status": "success"},
            ],
            outcome="success",
            duration_ms=150 + i * 10,  # Gets faster each time
            timestamp=1000000 + i * 100,
            authority="economic",
        )

        await learning_system.learn_from_trace(trace)
        print(f"  Execution {i+1}: {trace.tool_sequence()} → SUCCESS")

    # Check what patterns emerged
    patterns = learning_system.pattern_extractor.get_patterns_for_user(user_id)
    print(f"\nPatterns learned: {len(patterns)}")
    for pattern in patterns:
        print(f"  Pattern: {pattern.pattern}")
        print(f"    Frequency: {pattern.frequency}")
        print(f"    Success rate: {pattern.success_rate:.1%}")
        print(f"    Confidence: {pattern.confidence:.1%}")

    # Get statistics
    stats = learning_system.get_learning_stats(user_id)
    print(f"\nLearning statistics:")
    print(f"  Total executions: {stats['total_executions']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
    print(f"  Learning readiness: {stats['learning_readiness']:.1%}")


# =============================================================================
# Example 2: Prediction and Preloading
# =============================================================================


async def example_prediction():
    """
    After learning, system predicts next action.
    EHSA can preload tools.
    """
    print("\n[Example 2] Prediction and Preloading")
    print("-" * 80)

    learning_system = get_learning_system()
    user_id = "user_example_2"

    # Build pattern history
    for i in range(5):
        trace = ExecutionTrace(
            execution_id=f"exec_{i}",
            user_id=user_id,
            goal="Analyze leads",
            steps=[
                {"tool_id": "crm.analyze", "status": "success"},
                {"tool_id": "analytics.report", "status": "success"},
            ],
            outcome="success",
            duration_ms=200,
            timestamp=2000000 + i * 100,
            authority="economic",
        )
        await learning_system.learn_from_trace(trace)

    # Now make a prediction
    prediction = await learning_system.make_prediction(user_id, "Analyze leads")

    if prediction:
        print(f"Prediction for goal 'Analyze leads':")
        print(f"  Next action: {prediction.next_action}")
        print(f"  Confidence: {prediction.confidence:.1%}")

        # Get preload hints
        preload = learning_system.get_preload_hints(user_id, "Analyze leads")
        print(f"  Preload tools: {preload}")
    else:
        print("No prediction available yet")


# =============================================================================
# Example 3: Plan Optimization
# =============================================================================


async def example_plan_optimization():
    """
    EHSA optimizes plan based on learned successful patterns.
    """
    print("\n[Example 3] Plan Optimization")
    print("-" * 80)

    learning_system = get_learning_system()
    user_id = "user_example_3"

    # Build successful pattern history
    successful_order = ["analyzer", "reporter", "emailer"]
    for i in range(5):
        trace = ExecutionTrace(
            execution_id=f"exec_{i}",
            user_id=user_id,
            goal="Analyze and distribute report",
            steps=[
                {"tool_id": tool, "status": "success"}
                for tool in successful_order
            ],
            outcome="success",
            duration_ms=300,
            timestamp=3000000 + i * 100,
            authority="economic",
        )
        await learning_system.learn_from_trace(trace)

    # Try a different order
    initial_plan = [
        {"step_id": 1, "tool_id": "emailer"},
        {"step_id": 2, "tool_id": "analyzer"},
        {"step_id": 3, "tool_id": "reporter"},
    ]

    print("Initial plan: emailer → analyzer → reporter")

    # Optimize
    optimized = await learning_system.optimize_plan(
        user_id=user_id,
        goal="Analyze and distribute report",
        current_plan=initial_plan,
    )

    if optimized:
        optimized_order = " → ".join([s.get("tool_id") for s in optimized])
        print(f"Optimized plan: {optimized_order}")
    else:
        print("No optimization available")


# =============================================================================
# Example 4: Feedback and Reinforcement
# =============================================================================


async def example_feedback_loop():
    """
    Provide feedback signals to reinforce/penalize patterns.
    """
    print("\n[Example 4] Feedback and Reinforcement")
    print("-" * 80)

    learning_system = get_learning_system()
    user_id = "user_example_4"

    # Create two patterns: one successful, one less so
    trace_good = ExecutionTrace(
        execution_id="good_1",
        user_id=user_id,
        goal="Quick summary",
        steps=[
            {"tool_id": "analytics.summarize", "status": "success"},
        ],
        outcome="success",
        duration_ms=50,
        timestamp=4000000,
        authority="public",
    )

    trace_slow = ExecutionTrace(
        execution_id="slow_1",
        user_id=user_id,
        goal="Deep analysis",
        steps=[
            {"tool_id": "analytics.analyze", "status": "success"},
            {"tool_id": "analytics.deep_analyze", "status": "success"},
        ],
        outcome="success",
        duration_ms=500,
        timestamp=4000100,
        authority="public",
    )

    await learning_system.learn_from_trace(trace_good)
    await learning_system.learn_from_trace(trace_slow)

    # Give positive feedback to good pattern
    feedback_good = LearningFeedback(
        execution_id="good_1",
        user_id=user_id,
        success=True,
        reward=1.0,
        penalty=0.0,
        reason="Fast execution",
        timestamp=4000010,
    )
    await learning_system.provide_feedback(feedback_good)

    # Give negative feedback to slow pattern
    feedback_slow = LearningFeedback(
        execution_id="slow_1",
        user_id=user_id,
        success=True,
        reward=0.5,  # Partial reward (worked, but slow)
        penalty=0.5,  # Penalize for slowness
        reason="Slow execution",
        timestamp=4000110,
    )
    await learning_system.provide_feedback(feedback_slow)

    patterns = learning_system.pattern_extractor.get_patterns_for_user(user_id)
    for pattern in patterns:
        print(f"Pattern: {pattern.pattern}")
        print(f"  Success rate: {pattern.success_rate:.1%}")
        print(f"  Avg duration: {pattern.avg_duration_ms:.0f}ms")


# =============================================================================
# Example 5: Enhanced EHSA with Learning
# =============================================================================


async def example_enhanced_ehsa():
    """
    Use EnhancedEHSA to execute with learning integration.
    """
    print("\n[Example 5] Enhanced EHSA with Learning")
    print("-" * 80)

    ehsa = EnhancedEHSA()
    register_analytics_tools()

    user_id = "user_example_5"

    # Callback to monitor learning
    async def on_learning_update(event):
        if event["type"] == "prediction":
            print(f"  Prediction: {event['next_action']} (confidence: {event['confidence']:.0%})")
        elif event["type"] == "optimization":
            print(f"  Optimization: {event['optimized_steps']} steps (was {event['original_steps']})")

    # Execute with learning
    result = await ehsa.execute_with_learning(
        goal="Summarize the data",
        user_id=user_id,
        twin_context={"data": [1, 2, 3, 4, 5]},
        authority="public",
        learning_callback=on_learning_update,
    )

    print(f"Execution result: {result.status}")

    # Get insights about what was learned
    insights = await ehsa.get_twin_insights(user_id)
    print(f"\nTwin insights:")
    print(f"  Total executions: {insights['total_executions']}")
    print(f"  Learning readiness: {insights['learning_readiness']:.1%}")


# =============================================================================
# Example 6: Proactive Recommendations
# =============================================================================


async def example_proactive_recommendations():
    """
    System suggests next action based on user history.
    """
    print("\n[Example 6] Proactive Recommendations")
    print("-" * 80)

    ehsa = EnhancedEHSA()
    user_id = "user_example_6"

    # Simulate history
    learning = ehsa.learning_system
    for i in range(3):
        # User always does: analyze → report → email
        trace = ExecutionTrace(
            execution_id=f"exec_{i}",
            user_id=user_id,
            goal="Analysis workflow",
            steps=[
                {"tool_id": "analyzer", "status": "success"},
                {"tool_id": "reporter", "status": "success"},
                {"tool_id": "emailer", "status": "success"},
            ],
            outcome="success",
            duration_ms=300,
            timestamp=6000000 + i * 100,
            authority="economic",
        )
        await learning.learn_from_trace(trace)

    # Get suggestion for next action
    suggestion = await ehsa.suggest_next_action(user_id)

    if suggestion:
        print(f"Suggestion for {user_id}:")
        print(f"  After 'Analysis workflow'")
        print(f"  Next likely goal: {suggestion['suggested_goal']}")
        print(f"  Confidence: {suggestion['confidence']:.0%}")
    else:
        print("Not enough history for suggestions yet")


# =============================================================================
# Main: Run all examples
# =============================================================================


async def run_all_examples():
    """Run all memory examples."""
    print("=" * 80)
    print("Memory Intelligence Examples — Phase 2.3")
    print("=" * 80)

    await example_learning_pattern()
    await example_prediction()
    await example_plan_optimization()
    await example_feedback_loop()
    await example_enhanced_ehsa()
    await example_proactive_recommendations()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_examples())
