{ pkgs, ... }: {
  channel = "stable-24.05"; 
  packages = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.virtualenv
  ];
  env = {};
  idx = {
    extensions = [
      "ms-python.python"
    ];
  };
}
