function AuthInput({
  id,
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  required = false,
  minLength,
  autoComplete,
  icon,
  rightAction,
  ariaLabel,
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-slate-700">
        {label}
      </label>
      <div className="relative">
        {icon ? <span className="pointer-events-none absolute inset-y-0 left-0 grid w-11 place-items-center text-slate-400">{icon}</span> : null}
        <input
          id={id}
          aria-label={ariaLabel || label}
          type={type}
          value={value}
          onChange={onChange}
          required={required}
          minLength={minLength}
          autoComplete={autoComplete}
          placeholder={placeholder}
          className={`w-full rounded-xl border border-slate-300 bg-white py-3 text-sm text-slate-900 outline-none transition duration-200 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/20 ${
            icon ? "pl-11" : "pl-4"
          } ${rightAction ? "pr-12" : "pr-4"}`}
        />
        {rightAction ? <div className="absolute inset-y-0 right-0 grid w-12 place-items-center">{rightAction}</div> : null}
      </div>
    </div>
  );
}

export default AuthInput;
