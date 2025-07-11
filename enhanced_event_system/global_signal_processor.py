#!/usr/bin/env python3
"""
Global Signal Processor for TORE Matrix Labs V1 Enhancement

This module provides centralized signal processing and coordination for the
enhanced V1 system, managing complex signal chains and cross-component
communication with V2-style patterns.
"""

import logging
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .event_types_v1 import EventTypeV1, V1EventData, EventPriority
from .unified_event_bus import UnifiedEventBus


class ProcessingState(Enum):
    """Signal processing states."""
    IDLE = "idle"
    PROCESSING = "processing"
    COORDINATING = "coordinating"
    ERROR = "error"
    RECOVERY = "recovery"


@dataclass
class SignalChain:
    """Represents a chain of related signals/events."""
    
    chain_id: str
    trigger_event: EventTypeV1
    expected_events: List[EventTypeV1]
    timeout_seconds: float = 30.0
    
    # State tracking
    started_at: Optional[datetime] = None
    received_events: List[V1EventData] = field(default_factory=list)
    completed: bool = False
    failed: bool = False
    error_message: Optional[str] = None
    
    def is_complete(self) -> bool:
        """Check if all expected events have been received."""
        received_types = {event.event_type for event in self.received_events}
        expected_types = set(self.expected_events)
        return expected_types.issubset(received_types)
    
    def is_expired(self) -> bool:
        """Check if the chain has expired."""
        if self.started_at is None:
            return False
        elapsed = (datetime.now() - self.started_at).total_seconds()
        return elapsed > self.timeout_seconds
    
    def add_event(self, event: V1EventData) -> bool:
        """Add an event to the chain if it belongs."""
        if event.event_type in self.expected_events:
            self.received_events.append(event)
            return True
        return False


@dataclass
class ProcessingRule:
    """Rule for coordinated processing across components."""
    
    rule_id: str
    description: str
    trigger_events: Set[EventTypeV1]
    coordination_callback: Callable[[List[V1EventData]], None]
    requires_all: bool = True  # If True, all events must occur
    timeout_seconds: float = 10.0
    priority: EventPriority = EventPriority.NORMAL
    
    # State
    pending_events: List[V1EventData] = field(default_factory=list)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


class GlobalSignalProcessor:
    """
    Centralized signal processor for coordinating complex workflows.
    
    This processor manages:
    1. Cross-component signal coordination
    2. Signal chain tracking and completion
    3. Workflow orchestration
    4. Error recovery and retries
    5. Performance monitoring
    """
    
    def __init__(self, event_bus: UnifiedEventBus):
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # Processing state
        self.state = ProcessingState.IDLE
        self.processing_lock = threading.RLock()
        
        # Signal chains and workflows
        self.active_chains: Dict[str, SignalChain] = {}
        self.completed_chains: deque = deque(maxlen=100)
        self.processing_rules: Dict[str, ProcessingRule] = {}
        
        # Component coordination
        self.component_states: Dict[str, Dict[str, Any]] = {}
        self.component_dependencies: Dict[str, Set[str]] = {}
        self.coordination_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Performance monitoring
        self.processing_stats = {
            'chains_created': 0,
            'chains_completed': 0,
            'chains_failed': 0,
            'rules_triggered': 0,
            'coordination_events': 0,
            'average_chain_time': 0.0
        }
        
        # Error handling and recovery
        self.error_handlers: Dict[EventTypeV1, List[Callable]] = defaultdict(list)
        self.recovery_strategies: Dict[str, Callable] = {}
        
        # Workflow patterns
        self._setup_common_workflows()
        
        # Subscribe to all events for processing
        self._subscribe_to_events()
        
        # Start maintenance thread
        self.maintenance_thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self.shutdown_event = threading.Event()
        self.maintenance_thread.start()
        
        self.logger.info("Global signal processor initialized")
    
    def _setup_common_workflows(self):
        """Set up common workflow patterns for V1 system."""
        
        # Document processing workflow
        self.register_signal_chain(
            "document_processing_workflow",
            trigger_event=EventTypeV1.DOCUMENT_LOADED,
            expected_events=[
                EventTypeV1.DOCUMENT_PROCESSING_STARTED,
                EventTypeV1.EXTRACTION_COMPLETED,
                EventTypeV1.QUALITY_ASSESSMENT_COMPLETED,
                EventTypeV1.DOCUMENT_PROCESSING_COMPLETED
            ],
            timeout_seconds=300.0  # 5 minutes
        )
        
        # Manual validation workflow
        self.register_signal_chain(
            "manual_validation_workflow",
            trigger_event=EventTypeV1.MANUAL_VALIDATION_STARTED,
            expected_events=[
                EventTypeV1.AREA_SELECTED,
                EventTypeV1.AREA_EXCLUDED,
                EventTypeV1.MANUAL_VALIDATION_COMPLETED
            ],
            timeout_seconds=1800.0  # 30 minutes
        )
        
        # QA validation workflow
        self.register_signal_chain(
            "qa_validation_workflow", 
            trigger_event=EventTypeV1.QA_VALIDATION_STARTED,
            expected_events=[
                EventTypeV1.PAGE_VALIDATION_STARTED,
                EventTypeV1.VALIDATION_ISSUE_DETECTED,
                EventTypeV1.VALIDATION_ISSUE_RESOLVED,
                EventTypeV1.QA_VALIDATION_COMPLETED
            ],
            timeout_seconds=600.0  # 10 minutes
        )
        
        # PDF highlighting coordination
        self.register_processing_rule(
            "pdf_highlighting_coordination",
            "Coordinate PDF highlighting across components",
            trigger_events={
                EventTypeV1.PDF_LOCATION_HIGHLIGHTED,
                EventTypeV1.PDF_TEXT_SELECTION_HIGHLIGHTED
            },
            coordination_callback=self._coordinate_pdf_highlighting,
            requires_all=False
        )
        
        # Document state synchronization
        self.register_processing_rule(
            "document_state_sync",
            "Synchronize document state across widgets",
            trigger_events={
                EventTypeV1.DOCUMENT_STATE_CHANGED,
                EventTypeV1.AREA_STORAGE_UPDATED
            },
            coordination_callback=self._coordinate_document_state,
            requires_all=False
        )
    
    def register_signal_chain(self,
                             chain_id: str,
                             trigger_event: EventTypeV1,
                             expected_events: List[EventTypeV1],
                             timeout_seconds: float = 30.0) -> bool:
        """
        Register a signal chain for tracking.
        
        Args:
            chain_id: Unique identifier for the chain
            trigger_event: Event that starts the chain
            expected_events: Events expected to complete the chain
            timeout_seconds: Timeout for chain completion
            
        Returns:
            True if registered successfully
        """
        try:
            chain = SignalChain(
                chain_id=chain_id,
                trigger_event=trigger_event,
                expected_events=expected_events,
                timeout_seconds=timeout_seconds
            )
            
            with self.processing_lock:
                # Store chain template (not active until triggered)
                setattr(self, f"_chain_template_{chain_id}", chain)
            
            self.logger.debug(f"Registered signal chain: {chain_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register signal chain {chain_id}: {e}")
            return False
    
    def register_processing_rule(self,
                                rule_id: str,
                                description: str,
                                trigger_events: Set[EventTypeV1],
                                coordination_callback: Callable[[List[V1EventData]], None],
                                requires_all: bool = True,
                                timeout_seconds: float = 10.0,
                                priority: EventPriority = EventPriority.NORMAL) -> bool:
        """
        Register a processing rule for event coordination.
        
        Args:
            rule_id: Unique identifier for the rule
            description: Description of the rule
            trigger_events: Events that trigger this rule
            coordination_callback: Function to call when rule is triggered
            requires_all: Whether all events must occur
            timeout_seconds: Timeout for rule processing
            priority: Processing priority
            
        Returns:
            True if registered successfully
        """
        try:
            rule = ProcessingRule(
                rule_id=rule_id,
                description=description,
                trigger_events=trigger_events,
                coordination_callback=coordination_callback,
                requires_all=requires_all,
                timeout_seconds=timeout_seconds,
                priority=priority
            )
            
            with self.processing_lock:
                self.processing_rules[rule_id] = rule
            
            self.logger.debug(f"Registered processing rule: {rule_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register processing rule {rule_id}: {e}")
            return False
    
    def register_component_dependency(self, component: str, depends_on: List[str]):
        """Register component dependencies for coordination."""
        with self.processing_lock:
            self.component_dependencies[component] = set(depends_on)
        self.logger.debug(f"Registered dependencies for {component}: {depends_on}")
    
    def update_component_state(self, component: str, state: Dict[str, Any]):
        """Update component state for coordination."""
        with self.processing_lock:
            if component not in self.component_states:
                self.component_states[component] = {}
            self.component_states[component].update(state)
        
        # Trigger coordination callbacks
        self._trigger_coordination_callbacks(component, state)
    
    def _subscribe_to_events(self):
        """Subscribe to all relevant events for processing."""
        # Subscribe to all event types for processing
        for event_type in EventTypeV1:
            self.event_bus.subscribe(
                event_type,
                self._process_event,
                subscriber_id=f"global_processor_{event_type.value}",
                priority=EventPriority.HIGH
            )
    
    def _process_event(self, event: V1EventData):
        """Process incoming events for chains and rules."""
        try:
            with self.processing_lock:
                self.state = ProcessingState.PROCESSING
                
                # Check for signal chain triggers
                self._check_chain_triggers(event)
                
                # Update existing chains
                self._update_active_chains(event)
                
                # Check processing rules
                self._check_processing_rules(event)
                
                # Update component coordination
                self._update_coordination(event)
                
                self.state = ProcessingState.IDLE
                
        except Exception as e:
            self.state = ProcessingState.ERROR
            self.logger.error(f"Error processing event {event.event_type.value}: {e}")
            self._handle_processing_error(event, e)
    
    def _check_chain_triggers(self, event: V1EventData):
        """Check if event triggers any signal chains."""
        # Check all chain templates for triggers
        for attr_name in dir(self):
            if attr_name.startswith('_chain_template_'):
                template = getattr(self, attr_name)
                if isinstance(template, SignalChain) and template.trigger_event == event.event_type:
                    # Create active chain from template
                    chain_id = f"{template.chain_id}_{event.event_id[:8]}"
                    active_chain = SignalChain(
                        chain_id=chain_id,
                        trigger_event=template.trigger_event,
                        expected_events=template.expected_events.copy(),
                        timeout_seconds=template.timeout_seconds,
                        started_at=datetime.now()
                    )
                    active_chain.add_event(event)
                    
                    self.active_chains[chain_id] = active_chain
                    self.processing_stats['chains_created'] += 1
                    
                    self.logger.debug(f"Started signal chain: {chain_id}")
    
    def _update_active_chains(self, event: V1EventData):
        """Update active signal chains with new events."""
        completed_chains = []
        
        for chain_id, chain in self.active_chains.items():
            if chain.add_event(event):
                self.logger.debug(f"Added event {event.event_type.value} to chain {chain_id}")
                
                # Check if chain is complete
                if chain.is_complete():
                    chain.completed = True
                    completed_chains.append(chain_id)
                    self.processing_stats['chains_completed'] += 1
                    
                    # Calculate completion time
                    if chain.started_at:
                        completion_time = (datetime.now() - chain.started_at).total_seconds()
                        self._update_average_chain_time(completion_time)
                    
                    self.logger.info(f"Signal chain completed: {chain_id}")
        
        # Move completed chains to history
        for chain_id in completed_chains:
            chain = self.active_chains.pop(chain_id)
            self.completed_chains.append(chain)
    
    def _check_processing_rules(self, event: V1EventData):
        """Check if event triggers processing rules."""
        for rule_id, rule in self.processing_rules.items():
            if event.event_type in rule.trigger_events:
                rule.pending_events.append(event)
                
                # Check if rule should be triggered
                should_trigger = False
                
                if rule.requires_all:
                    # All events must be present
                    received_types = {e.event_type for e in rule.pending_events}
                    should_trigger = rule.trigger_events.issubset(received_types)
                else:
                    # Any event triggers the rule
                    should_trigger = True
                
                if should_trigger:
                    try:
                        rule.coordination_callback(rule.pending_events.copy())
                        rule.last_triggered = datetime.now()
                        rule.trigger_count += 1
                        rule.pending_events.clear()
                        
                        self.processing_stats['rules_triggered'] += 1
                        self.logger.debug(f"Triggered processing rule: {rule_id}")
                        
                    except Exception as e:
                        self.logger.error(f"Error in processing rule {rule_id}: {e}")
    
    def _coordinate_pdf_highlighting(self, events: List[V1EventData]):
        """Coordinate PDF highlighting across components."""
        self.logger.debug("Coordinating PDF highlighting")
        
        # Extract highlighting data
        for event in events:
            if event.event_type == EventTypeV1.PDF_LOCATION_HIGHLIGHTED:
                coordinates = event.get_data('coordinates', {})
                # Publish coordination event
                self.event_bus.publish(
                    EventTypeV1.PDF_COORDINATE_MAPPED,
                    "global_processor",
                    {
                        'source_event_id': event.event_id,
                        'coordinates': coordinates,
                        'highlight_type': 'location'
                    }
                )
            elif event.event_type == EventTypeV1.PDF_TEXT_SELECTION_HIGHLIGHTED:
                text_selection = event.get_data('text_selection', '')
                coordinates = event.get_data('coordinates', {})
                # Publish coordination event
                self.event_bus.publish(
                    EventTypeV1.PDF_COORDINATE_MAPPED,
                    "global_processor",
                    {
                        'source_event_id': event.event_id,
                        'text_selection': text_selection,
                        'coordinates': coordinates,
                        'highlight_type': 'text_selection'
                    }
                )
        
        self.processing_stats['coordination_events'] += 1
    
    def _coordinate_document_state(self, events: List[V1EventData]):
        """Coordinate document state across widgets."""
        self.logger.debug("Coordinating document state")
        
        # Collect state updates
        state_updates = {}
        
        for event in events:
            if event.event_type == EventTypeV1.DOCUMENT_STATE_CHANGED:
                doc_id = event.get_data('document_id', '')
                if doc_id:
                    state_updates[doc_id] = event.data
            elif event.event_type == EventTypeV1.AREA_STORAGE_UPDATED:
                # Handle area storage updates
                area_data = event.get_data('area_data', {})
                doc_id = area_data.get('document_id', '')
                if doc_id:
                    if doc_id not in state_updates:
                        state_updates[doc_id] = {}
                    state_updates[doc_id]['areas_updated'] = True
                    state_updates[doc_id]['area_data'] = area_data
        
        # Publish consolidated state updates
        for doc_id, updates in state_updates.items():
            self.event_bus.publish(
                EventTypeV1.STATE_SAVED,
                "global_processor",
                {
                    'document_id': doc_id,
                    'state_updates': updates,
                    'coordination_source': 'global_processor'
                }
            )
        
        self.processing_stats['coordination_events'] += 1
    
    def _update_coordination(self, event: V1EventData):
        """Update cross-component coordination."""
        sender = event.sender
        
        # Update component state tracking
        if sender not in self.component_states:
            self.component_states[sender] = {}
        
        self.component_states[sender]['last_event'] = event.event_type.value
        self.component_states[sender]['last_update'] = datetime.now()
        
        # Check dependencies
        if sender in self.component_dependencies:
            dependencies = self.component_dependencies[sender]
            ready_dependencies = []
            
            for dep in dependencies:
                if dep in self.component_states:
                    dep_state = self.component_states[dep]
                    # Check if dependency is ready (simple check for last update time)
                    last_update = dep_state.get('last_update')
                    if last_update and (datetime.now() - last_update).total_seconds() < 60:
                        ready_dependencies.append(dep)
            
            # If all dependencies are ready, trigger coordination
            if len(ready_dependencies) == len(dependencies):
                self._trigger_coordination_callbacks(sender, event.data)
    
    def _trigger_coordination_callbacks(self, component: str, data: Dict[str, Any]):
        """Trigger coordination callbacks for a component."""
        callbacks = self.coordination_callbacks.get(component, [])
        for callback in callbacks:
            try:
                callback(component, data)
            except Exception as e:
                self.logger.error(f"Error in coordination callback for {component}: {e}")
    
    def _handle_processing_error(self, event: V1EventData, error: Exception):
        """Handle processing errors with recovery strategies."""
        error_handlers = self.error_handlers.get(event.event_type, [])
        
        for handler in error_handlers:
            try:
                handler(event, error)
            except Exception as e:
                self.logger.error(f"Error in error handler: {e}")
        
        # Try recovery strategy
        if event.event_type.value in self.recovery_strategies:
            recovery_strategy = self.recovery_strategies[event.event_type.value]
            try:
                recovery_strategy(event, error)
                self.logger.info(f"Recovery attempted for {event.event_type.value}")
            except Exception as e:
                self.logger.error(f"Recovery strategy failed: {e}")
    
    def _maintenance_loop(self):
        """Maintenance loop for cleanup and monitoring."""
        while not self.shutdown_event.wait(30):  # Run every 30 seconds
            try:
                self._cleanup_expired_chains()
                self._cleanup_expired_rules()
                self._monitor_performance()
            except Exception as e:
                self.logger.error(f"Error in maintenance loop: {e}")
    
    def _cleanup_expired_chains(self):
        """Clean up expired signal chains."""
        expired_chains = []
        
        with self.processing_lock:
            for chain_id, chain in self.active_chains.items():
                if chain.is_expired():
                    expired_chains.append(chain_id)
                    chain.failed = True
                    chain.error_message = "Chain timeout"
                    self.processing_stats['chains_failed'] += 1
        
        # Move expired chains to history
        for chain_id in expired_chains:
            chain = self.active_chains.pop(chain_id)
            self.completed_chains.append(chain)
            self.logger.warning(f"Signal chain expired: {chain_id}")
    
    def _cleanup_expired_rules(self):
        """Clean up expired processing rule events."""
        current_time = datetime.now()
        
        with self.processing_lock:
            for rule in self.processing_rules.values():
                # Remove events older than timeout
                rule.pending_events = [
                    event for event in rule.pending_events
                    if (current_time - event.timestamp).total_seconds() < rule.timeout_seconds
                ]
    
    def _monitor_performance(self):
        """Monitor and log performance metrics."""
        if self.processing_stats['chains_created'] > 0:
            completion_rate = (
                self.processing_stats['chains_completed'] / 
                self.processing_stats['chains_created']
            )
            
            self.logger.debug(
                f"Signal processing stats: "
                f"chains_created={self.processing_stats['chains_created']}, "
                f"completion_rate={completion_rate:.2f}, "
                f"avg_time={self.processing_stats['average_chain_time']:.2f}s"
            )
    
    def _update_average_chain_time(self, completion_time: float):
        """Update average chain completion time."""
        current_avg = self.processing_stats['average_chain_time']
        completed_count = self.processing_stats['chains_completed']
        
        if completed_count > 1:
            new_avg = ((current_avg * (completed_count - 1)) + completion_time) / completed_count
            self.processing_stats['average_chain_time'] = new_avg
        else:
            self.processing_stats['average_chain_time'] = completion_time
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        with self.processing_lock:
            stats = self.processing_stats.copy()
            stats.update({
                'active_chains': len(self.active_chains),
                'processing_rules': len(self.processing_rules),
                'component_states': len(self.component_states),
                'current_state': self.state.value
            })
        return stats
    
    def get_active_chains_info(self) -> Dict[str, Any]:
        """Get information about active signal chains."""
        with self.processing_lock:
            chains_info = {}
            for chain_id, chain in self.active_chains.items():
                chains_info[chain_id] = {
                    'trigger_event': chain.trigger_event.value,
                    'expected_events': [e.value for e in chain.expected_events],
                    'received_events': [e.event_type.value for e in chain.received_events],
                    'started_at': chain.started_at.isoformat() if chain.started_at else None,
                    'is_complete': chain.is_complete(),
                    'is_expired': chain.is_expired()
                }
        return chains_info
    
    def shutdown(self):
        """Shutdown the global signal processor."""
        self.logger.info("Shutting down global signal processor")
        self.shutdown_event.set()
        
        if self.maintenance_thread.is_alive():
            self.maintenance_thread.join(timeout=5.0)
        
        self.logger.info("Global signal processor shutdown complete")