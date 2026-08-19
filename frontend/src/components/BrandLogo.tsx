import icon from "../utils/Images/Icon.png";

interface BrandLogoProps {
  size?: number;
}

export function BrandLogo({ size = 28 }: BrandLogoProps) {
  return <img src={icon} alt="BridgeScout" width={size} height={size} className="brand-icon" />;
}
