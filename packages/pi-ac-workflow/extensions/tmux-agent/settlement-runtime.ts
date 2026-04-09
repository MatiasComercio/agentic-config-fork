type BridgeEventDirection = "system" | "parent_to_child" | "child_to_parent";

type BridgeEventType =
	| "launched"
	| "instruction"
	| "answer"
	| "clarification"
	| "completion"
	| "question"
	| "blocker"
	| "progress"
	| "failure"
	| "exited"
	| "shutdown_request"
	| "closeout";

export type NotificationMode = "notify" | "notify-and-follow-up" | "silent";
export type SettledTerminalState = "settled_completion" | "settled_failure" | "settled_blocked" | "settled_waiting_on_parent" | "protocol_violation";
export type BridgeSettlementState = "running" | SettledTerminalState;

export interface BridgeSettlementEvent {
	eventId: string;
	direction: BridgeEventDirection;
	type: BridgeEventType;
	requiresResponse?: boolean;
}

export interface BridgeNotificationConfig {
	notificationMode: NotificationMode;
}

export interface BridgeSettlementEvaluation<TEvent extends BridgeSettlementEvent> {
	settledState: BridgeSettlementState;
	terminalEvent?: TEvent;
	protocolViolationReason?: string;
}

function hasBridgeExitEvent<TEvent extends BridgeSettlementEvent>(events: TEvent[]): boolean {
	return events.some((event) => event.direction === "system" && event.type === "exited");
}

function isTerminalDeclarationBridgeEvent(event: BridgeSettlementEvent): boolean {
	return event.direction === "child_to_parent" && (event.type === "closeout" || event.type === "failure" || event.type === "blocker" || event.type === "question");
}

function mapBridgeTerminalEventToSettledState(event: BridgeSettlementEvent): SettledTerminalState {
	switch (event.type) {
		case "closeout":
			return "settled_completion";
		case "failure":
			return "settled_failure";
		case "blocker":
			return "settled_blocked";
		case "question":
			return "settled_waiting_on_parent";
		default:
			throw new Error(`Unsupported terminal bridge event type: ${event.type}`);
	}
}

export function evaluateBridgeSettlement<TEvent extends BridgeSettlementEvent>(events: TEvent[]): BridgeSettlementEvaluation<TEvent> {
	const childExited = hasBridgeExitEvent(events);
	if (!childExited) {
		return { settledState: "running" };
	}

	const childReports = events.filter((event) => event.direction === "child_to_parent");
	const closeoutEvents = childReports.filter((event) => event.type === "closeout");
	if (closeoutEvents.length > 1) {
		return {
			settledState: "protocol_violation",
			protocolViolationReason: "Multiple closeout declarations were emitted.",
		};
	}
	if (closeoutEvents.length === 1) {
		const closeoutEvent = closeoutEvents[0];
		const closeoutIndex = childReports.findIndex((event) => event.eventId === closeoutEvent.eventId);
		const postCloseoutEvent = closeoutIndex === -1 ? undefined : childReports.slice(closeoutIndex + 1)[0];
		if (postCloseoutEvent) {
			return {
				settledState: "protocol_violation",
				protocolViolationReason: `Post-closeout child report detected: ${postCloseoutEvent.type} (${postCloseoutEvent.eventId})`,
			};
		}
		return {
			settledState: "settled_completion",
			terminalEvent: closeoutEvent,
		};
	}

	const declaredNonSuccessEvent = [...childReports].reverse().find((event) => isTerminalDeclarationBridgeEvent(event));
	if (!declaredNonSuccessEvent) {
		return {
			settledState: "protocol_violation",
			protocolViolationReason: "Child exited without a valid terminal declaration.",
		};
	}
	return {
		settledState: mapBridgeTerminalEventToSettledState(declaredNonSuccessEvent),
		terminalEvent: declaredNonSuccessEvent,
	};
}

export function shouldDeliverBridgeEventToParent(event: Pick<BridgeSettlementEvent, "type">): boolean {
	return event.type !== "closeout";
}

export function shouldTriggerTurnForEvent(event: Pick<BridgeSettlementEvent, "type" | "requiresResponse">, launch: BridgeNotificationConfig): boolean {
	if (launch.notificationMode === "silent") return false;
	if (event.type === "closeout") return false;
	if (event.type === "progress") return Boolean(event.requiresResponse);
	if (event.type === "question" || event.type === "blocker") return true;
	if (event.type === "failure") return true;
	if (event.requiresResponse) return true;
	return launch.notificationMode === "notify-and-follow-up";
}

export function shouldTriggerTurnForSettledState(state: SettledTerminalState, launch: BridgeNotificationConfig): boolean {
	if (launch.notificationMode === "silent") return false;
	if (state === "settled_completion") return launch.notificationMode === "notify-and-follow-up";
	return true;
}
