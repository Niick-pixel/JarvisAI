// Convenience aliases over the generated schema. Every shape here traces back to a Pydantic
// model on the backend; nothing in this file declares a shape of its own (rule 0.5).
import type { components } from "./schema.gen";

type S = components["schemas"];

export type Conversation = S["Conversation"];
export type ConversationTree = S["ConversationTree"];
export type Message = S["Message"];
export type Role = Message["role"];
export type ContextAssembly = S["ContextAssembly"];
export type ContextBlock = S["ContextBlock"];
export type EvictionNotice = S["EvictionNotice"];
export type ModelInfo = S["ModelInfo"];
export type ModelOption = S["ModelOption"];
export type SelectedModel = S["SelectedModel"];
export type SiblingSet = S["SiblingSet"];
export type BlockPref = S["BlockPref"];
export type ProviderInfo = S["ProviderInfo"];
export type HardwareReport = S["HardwareReport"];
export type ModelRecommendation = S["ModelRecommendation"];
export type VramBudget = S["VramBudget"];
export type SamplingParams = S["SamplingParams"];
export type ErrorBody = S["ErrorBody"];
export type Remedy = S["Remedy"];
export type Health = S["Health"];

export type AssemblyEvent = S["AssemblyEvent"];
export type RunEvent = S["RunEvent"];
export type TokenEvent = S["TokenEvent"];
export type UsageEvent = S["UsageEvent"];
export type DoneEvent = S["DoneEvent"];
export type ErrorEvent = S["ErrorEvent"];

/** The SSE union, exhaustively switchable because the discriminator comes from the backend. */
export type StreamEvent =
  | AssemblyEvent
  | RunEvent
  | TokenEvent
  | UsageEvent
  | DoneEvent
  | ErrorEvent;
export type MessageTokens = S["MessageTokens"];
export type TokenView = S["TokenView"];
export type Alternative = S["Alternative"];
export type NudgeMark = S["NudgeMark"];
export type LifetimeCounters = S["LifetimeCounters"];
export type HudSample = S["HudSample"];
export type MemoryEntry = S["MemoryEntry"];
export type MemoryBatch = S["MemoryBatch"];
export type MemoryCommit = S["Commit"];
export type Source = S["Source"];
export type IndexProgress = S["IndexProgress"];
export type RetrievalStatus = S["RetrievalStatus"];
export type OpenedChunk = S["OpenedChunk"];
export type SearchStatus = S["SearchStatus"];
export type ResearchReport = S["ResearchReport"];
export type CouncilMember = S["CouncilMember"];
export type CouncilAnswer = S["CouncilAnswer"];
export type AgreementCell = S["AgreementCell"];
export type CouncilVerdict = S["CouncilVerdict"];
export type ScoreboardRow = S["ScoreboardRow"];
export type CouncilReport = S["CouncilReport"];
export type PlanEvent = S["PlanEvent"];
export type CouncilEvent =
  | PlanEvent
  | S["AnswerStartEvent"]
  | S["AnswerTokenEvent"]
  | S["AnswerDoneEvent"]
  | S["AgreementEvent"]
  | S["VerdictEvent"]
  | S["CouncilDoneEvent"];
export type VoiceStatus = S["VoiceStatus"];
export type VoicePackProgress = S["VoicePackProgress"];
export type EngineStatus = S["EngineStatus"];
export type Transcript = S["Transcript"];
export type SpeakRequest = S["SpeakRequest"];
export type Job = S["Job"];
export type JobCreate = S["JobCreate"];
export type JobPatch = S["JobPatch"];
export type JobRun = S["JobRun"];
export type InboxItem = S["InboxItem"];
export type ToolInfo = S["ToolInfo"];
export type PendingCall = S["PendingCall"];
export type Decision = S["Decision"];
export type ToolGrant = S["ToolGrant"];
export type AuditEntry = S["AuditEntry"];
export type ExportResult = S["ExportResult"];
export type DownloadProgress = S["DownloadProgress"];
export type LaunchStatus = S["LaunchStatus"];
export type HomeStatus = S["HomeStatus"];
export type Device = S["Device"];
export type HomeAction = S["HomeActionRequest"]["action"];
export type AssistResult = S["AssistResult"];
export type ForecastStatus = S["ForecastStatus"];
export type ForecastJob = S["ForecastJob"];
export type ForecastResult = S["ForecastResult"];
export type BacktestResult = S["BacktestResult"];
export type Candle = S["Candle"];
export type ForecastStep = S["ForecastStep"];
export type SeriesInfo = S["SeriesInfo"];
export type ImportResult = S["ImportResult"];
export type UpdateStatus = S["UpdateStatus"];
export type FileRoot = S["Root"];
export type FileEntry = S["Entry"];
export type FileContent = S["FileContent"];
export type Proposal = S["Proposal"];
export type Hunk = S["Hunk"];
export type RunResult = S["RunResult"];
export type LocalModels = S["LocalModels"];
export type LocalModel = S["LocalModel"];
export type AgentTurn = S["AgentTurn"];
export type AgentTurnStarted = S["AgentTurnStarted"];
export type MemoryUse = S["MemoryUse"];
export type Briefing = S["Briefing"];
export type BriefingSettings = S["BriefingSettings"];
export type JobDraft = S["JobDraft"];
export type JobStats = S["JobStats"];
export type LiveStatus = S["LiveStatus"];
export type LiveSymbol = S["LiveSymbol"];
export type AlertRule = S["AlertRule"];
export type AlertRuleCreate = S["AlertRuleCreate"];
export type AlertEvent = S["AlertEvent"];
export type JournalStats = S["JournalStats"];
export type JournalImport = S["JournalImport"];
export type JournalAnswer = S["JournalAnswer"];
export type Trade = S["Trade"];
export type Breakdown = S["Breakdown"];
export type WakeStatus = S["WakeStatus"];
export type Attachment = S["Attachment"];
export type ImageStatus = S["ImageStatus"];
export type Generated = S["Generated"];
export type PhoneStatus = S["PhoneStatus"];
export type DataKind = S["DataKind"];
