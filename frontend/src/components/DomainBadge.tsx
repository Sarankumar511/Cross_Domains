interface DomainBadgeProps {
  domain: string;
}

export function DomainBadge({ domain }: DomainBadgeProps) {
  return <span className="domain-badge">{domain}</span>;
}
