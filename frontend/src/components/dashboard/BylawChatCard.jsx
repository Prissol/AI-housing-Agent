import { FiSend } from "react-icons/fi";

function BylawChatCard({ messages, question, onQuestionChange, onSend, chatLoading, chatError }) {
  return (
    <section className="space-y-3 border-t border-slate-200 pt-6" aria-label="By-law assistant chatbot">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-700">Assistant</p>
        <h2 className="mt-1 text-2xl font-semibold text-slate-950">By-law Chatbot</h2>
      </div>

      <div className="max-h-72 space-y-2 overflow-y-auto rounded-xl border border-slate-200 bg-white p-3">
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`rounded-xl px-3 py-2 text-sm ${
              message.role === "user" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700"
            }`}
          >
            <p className="font-semibold">{message.role === "user" ? "You" : "Bylaw Bot"}</p>
            <p className="mt-1 whitespace-pre-wrap">{message.text}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !chatLoading) onSend();
          }}
          className="min-w-[180px] flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/20"
          placeholder="Ask about setbacks, height limits, parking..."
          aria-label="Ask by-law assistant"
        />
        <button
          type="button"
          onClick={onSend}
          disabled={chatLoading}
          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
        >
          <FiSend size={14} />
          {chatLoading ? "Sending..." : "Send"}
        </button>
      </div>
      {chatError ? <p className="text-sm text-rose-600">{chatError}</p> : null}
    </section>
  );
}

export default BylawChatCard;
