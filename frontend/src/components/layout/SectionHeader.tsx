import React from "react";

interface SectionHeaderProps {
  title: string;
  accentColor?: string; // e.g. "bg-indigo-500", "bg-cyan-500", "bg-emerald-500"
  className?: string;
  subtitle?: string;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  title,
  accentColor = "bg-indigo-500",
  className = "",
  subtitle,
}) => {
  return (
    <div className={`flex flex-col gap-1 mb-5 ${className}`}>
      <div className="flex items-center gap-2.5">
        <div className={`w-1 h-[18px] ${accentColor} rounded-sm shrink-0`} />
        <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider leading-none">
          {title}
        </h3>
      </div>
      {subtitle && (
        <p className="text-[11px] text-slate-500 font-medium pl-3.5">
          {subtitle}
        </p>
      )}
    </div>
  );
};
