import { useId } from 'react';

export default function Logo({ size = 30, ring = false }) {
  const id = useId().replace(/:/g, '');
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" aria-hidden="true">
      <defs>
        <radialGradient id={id} cx="35%" cy="30%" r="75%">
          <stop offset="0" stopColor="#FFFFFF" />
          <stop offset="0.55" stopColor="#F4F1E8" />
          <stop offset="1" stopColor="#D9C49A" />
        </radialGradient>
      </defs>
      <circle cx="18" cy="18" r="16" fill={`url(#${id})`} />
      {ring && <circle cx="18" cy="18" r="16.5" fill="none" stroke="#D9C49A" strokeWidth="1" />}
    </svg>
  );
}
