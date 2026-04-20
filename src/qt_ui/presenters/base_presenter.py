"""
Base presenter class for UI page presenters.

This module provides the foundation for presenter/controller classes that
manage business logic, state transitions, and communication between pages
and the underlying business logic.

The Presenter layer separates concerns:
- View (Pages): Rendering and user interaction only
- Presenter: Business logic, state management, callbacks
- Model (Services): Actual work (inventory, analysis, etc.)
"""

from __future__ import annotations

from typing import Any, Callable, Optional

try:
    from PySide6.QtCore import QObject, Signal
except ModuleNotFoundError:
    # Lightweight fallback used in non-Qt environments (e.g., CI/unit tests).
    class QObject:  # type: ignore[no-redef]
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

    class _BoundSignal:
        def __init__(self) -> None:
            self._subscribers = []

        def connect(self, callback) -> None:
            self._subscribers.append(callback)

        def disconnect(self, callback=None) -> None:
            if callback is None:
                self._subscribers.clear()
                return
            self._subscribers = [cb for cb in self._subscribers if cb is not callback]

        def emit(self, *args, **kwargs) -> None:
            for callback in list(self._subscribers):
                callback(*args, **kwargs)

    class Signal:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs) -> None:
            self._name = None

        def __set_name__(self, owner, name) -> None:
            self._name = name

        def __get__(self, instance, owner):
            if instance is None:
                return self
            storage_name = f"__signal_{self._name}"
            if not hasattr(instance, storage_name):
                setattr(instance, storage_name, _BoundSignal())
            return getattr(instance, storage_name)

from src.qt_ui.state import QtUiState


class BasePresenter(QObject):
    """
    Base class for all page presenters.

    A presenter manages the business logic and state for a single page.
    It receives user interactions from the view (page), processes them,
    updates the model (services), and emits signals to update the view.

    This class establishes the MVP (Model-View-Presenter) pattern:
    - View (Page): Renders UI and sends user interactions
    - Presenter: Handles business logic and state
    - Model (Services): Performs actual work

    Signals
    -------
    request_next : Signal()
        Emitted when the page should advance to the next step.
    request_back : Signal()
        Emitted when the page should go back to the previous step.
    page_title_changed : Signal(str)
        Emitted when the page title changes.
    error_occurred : Signal(str)
        Emitted when an error occurs during processing.
    loading_started : Signal()
        Emitted when a long-running operation starts.
    loading_finished : Signal()
        Emitted when a long-running operation finishes.
    """

    # Navigation signals
    request_next = Signal()
    request_back = Signal()

    # UI update signals
    page_title_changed = Signal(str)
    error_occurred = Signal(str)
    loading_started = Signal()
    loading_finished = Signal()

    def __init__(self, ui_state: QtUiState) -> None:
        """
        Initialize the presenter.

        Parameters
        ----------
        ui_state : QtUiState
            The shared UI state object.
        """
        super().__init__()
        self.ui_state = ui_state
        self._is_loading = False

    @property
    def is_loading(self) -> bool:
        """Check if a long-running operation is in progress."""
        return self._is_loading

    def set_loading(self, loading: bool) -> None:
        """
        Set the loading state and emit appropriate signals.

        Parameters
        ----------
        loading : bool
            True if an operation is starting, False if it's finishing.
        """
        self._is_loading = loading
        if loading:
            self.loading_started.emit()
        else:
            self.loading_finished.emit()

    def advance_to_next_page(self) -> None:
        """Emit signal to advance to the next page."""
        self.request_next.emit()

    def go_back_to_previous_page(self) -> None:
        """Emit signal to go back to the previous page."""
        self.request_back.emit()

    def emit_error(self, error_message: str) -> None:
        """
        Emit an error signal.

        Parameters
        ----------
        error_message : str
            The error message to display to the user.
        """
        self.error_occurred.emit(error_message)

    def update_page_title(self, title: str) -> None:
        """
        Update the page title.

        Parameters
        ----------
        title : str
            The new page title.
        """
        self.page_title_changed.emit(title)

    def on_page_shown(self) -> None:
        """
        Called when the page is shown (before it's visible to user).

        Override in subclasses to perform initialization or refresh logic.
        This is called BEFORE the page appears on screen.
        """
        pass

    def on_page_hidden(self) -> None:
        """
        Called when the page is about to be hidden.

        Override in subclasses to perform cleanup or save state.
        This is called AFTER the page disappears from screen.
        """
        pass

    def on_page_before_next(self) -> bool:
        """
        Called before advancing to the next page.

        Override in subclasses to validate state or perform final operations.
        Return False to prevent advancing, True to allow.

        Returns
        -------
        bool
            True if allowed to proceed to next page, False otherwise.
        """
        return True

    def on_page_before_previous(self) -> bool:
        """
        Called before going back to the previous page.

        Override in subclasses to validate state or perform cleanup.
        Return False to prevent going back, True to allow.

        Returns
        -------
        bool
            True if allowed to go back, False otherwise.
        """
        return True

    def refresh(self) -> None:
        """
        Refresh the presenter state based on current ui_state.

        Override in subclasses to update internal state when ui_state changes.
        This is called when the page needs to react to state changes.
        """
        pass

    def handle_error(self, error: Exception) -> None:
        """
        Handle an exception and emit appropriate error signal.

        Parameters
        ----------
        error : Exception
            The exception that occurred.
        """
        error_message = str(error) if str(error) else type(error).__name__
        self.emit_error(error_message)
