{
  pkgs ? import <nixpkgs> {},
  platform ? if pkgs.stdenv.isDarwin then "macosx_11_0" else "manylinux_2_28",
  arch ? if pkgs.stdenv.isAarch64 then "aarch64" else "x86_64",
  packages ? [ "llvm" ],
}:
let
  sources = builtins.fromJSON (builtins.readFile ./hugrenv.lock);
  version = sources.version;
  get-package = package: pkgs.fetchzip {
    url = let
      path="https://github.com/Quantinuum/hugrverse-env/releases/download/v${version}/hugrenv-${package}-${platform}_${arch}.tar.gz";
    in builtins.trace "fetching ${package} from ${path}" path;
    sha256 = sources.hashes.${platform}.${arch}.${package};
  };
in pkgs.symlinkJoin {
  name = "hugrenv-${version}-${pkgs.lib.concatStringsSep "-" [platform arch]}_${pkgs.lib.concatStringsSep "-" packages}";
  paths = map get-package packages;
}
