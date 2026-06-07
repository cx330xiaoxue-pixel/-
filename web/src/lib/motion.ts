/** Ease-out expo — cinematic deceleration curve */
export const easeOutExpo = [0.25, 0.46, 0.45, 0.94] as const;

/** Default spring config for layout animations */
export const springSnappy = {
  type: "spring" as const,
  stiffness: 500,
  damping: 35,
};

/** Stagger container for children */
export const staggerContainer = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1,
    },
  },
};

/** Fade-up item for staggered children */
export const fadeUpItem = {
  hidden: { y: 24, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      duration: 0.6,
      ease: easeOutExpo,
    },
  },
};
