import logo from "../assets/HomeMade_Logo.png";

export default function LoadingScreen() {
  return (
    <div className="w-full flex-1 flex flex-col justify-center items-center bg-background-primary overflow-hidden">
      <img
        src={logo}
        alt="HomeMade Logo"
        className="w-56 h-auto object-contain animate-pulse"
      />
    </div>
  );
}
