import React, { useEffect } from "react";
import { X } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";

export type DrawerSize = "sm" | "md" | "lg" | "xl" | "full";

export interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
  size?: DrawerSize;
  className?: string;
  hideCloseButton?: boolean;
}

const sizeConfig = {
  sm: "w-full max-w-[360px]",
  md: "w-full max-w-[480px]",
  lg: "w-full max-w-[640px]",
  xl: "w-full max-w-[800px]",
  full: "w-full md:w-[calc(100vw-32px)] md:m-4 rounded-2xl",
};

export function Drawer({
  isOpen,
  onClose,
  title,
  subtitle,
  footer,
  children,
  size = "md",
  className,
  hideCloseButton = false,
}: DrawerProps) {
  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "auto";
    }
    return () => {
      document.body.style.overflow = "auto";
    };
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="fixed inset-0 z-50 bg-obsidian-950/60 backdrop-blur-[4px]"
            onClick={onClose}
          />

          {/* Drawer Panel */}
          <motion.div
            initial={
              size === "full"
                ? { opacity: 0, scale: 0.95, y: 20 }
                : { x: "100%" }
            }
            animate={
              size === "full" ? { opacity: 1, scale: 1, y: 0 } : { x: 0 }
            }
            exit={
              size === "full"
                ? { opacity: 0, scale: 0.95, y: 20 }
                : { x: "100%" }
            }
            transition={{
              type: "spring",
              damping: 25,
              stiffness: 200,
              mass: 0.8,
            }}
            className={cn(
              "fixed z-50 flex flex-col bg-surface-base border-border-default shadow-[-10px_0_40px_rgba(0,0,0,0.5)] overflow-hidden",
              size === "full"
                ? "inset-0 md:inset-auto md:top-4 md:bottom-4 md:right-4 border bg-obsidian-900"
                : "top-0 right-0 bottom-0 border-l bg-obsidian-950",
              sizeConfig[size],
              className,
            )}
            style={size === "full" ? {} : { height: "100dvh" }}
          >
            {/* Header */}
            {(title || subtitle) && (
              <div className="flex-none px-6 py-5 border-b border-white/5 bg-surface-card/50">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex flex-col gap-1 min-w-0 flex-1">
                    {title && (
                      <h2 className="text-lg font-bold text-white tracking-tight leadng-tight truncate">
                        {title}
                      </h2>
                    )}
                    {subtitle && (
                      <p className="text-sm text-text-tertiary">{subtitle}</p>
                    )}
                  </div>
                  {!hideCloseButton && (
                    <button
                      onClick={onClose}
                      className="p-2 -mr-2 rounded-xl text-text-tertiary hover:text-white hover:bg-white/10 transition-colors shrink-0"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
              {children}
            </div>

            {/* Footer */}
            {footer && (
              <div className="flex-none px-6 py-4 border-t border-white/5 bg-surface-card/80 backdrop-blur-md">
                {footer}
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
