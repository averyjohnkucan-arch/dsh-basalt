#include "models/deepseek41/engram_external.hpp"
#include <iostream>
#include <fstream>
#include <cstring>
#include "basalt/ngram/ple_reader.hpp"
using basalt::models::deepseek41::external_engram_offset;
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    std::string root = argv[1], err;
    uint64_t off = 0;
    auto call = [&](const std::string& name, bool expected, uint64_t rows = 8, uint32_t bytes = 144,
                    int values = 256, int type = 20, std::vector<int> layers = {1,14}) {
        err.clear();
        const bool ok = external_engram_offset(root + "/" + name, rows, bytes, values, type, layers, off, err);
        if (ok != expected) { std::cerr << name << ": " << err << "\n"; std::exit(1); }
    };
    call("valid.gguf", true);
    call("wrong-width.gguf", false);
    call("wrong-layers.gguf", false);
    call("wrong-type.gguf", false);
    call("truncated.gguf", false);
    call("trailing.gguf", false);
    call("valid.gguf", false, 9);
    call("valid.gguf", false, 8, 144, 256, 39);
    call("valid.gguf", false, 8, 144, 256, 20, {14,1});
    call("missing.gguf", false);
    basalt::GgufFile actual(argv[2]);
    uint64_t rows = 0;
    for (const auto& t : actual.tensors()) rows += t.shape.at(1);
    if (!external_engram_offset(argv[2], rows, 144, 256, 20, {1,14}, off, err)) {
        std::cerr << err << "\n";
        return 1;
    }
    if (off != actual.data_start()) return 1;
    std::vector<uint32_t> ids={0,1,static_cast<uint32_t>(rows/2),static_cast<uint32_t>(rows-1)};
    for(uint32_t i=0;i<4096 && ids.size()<16;++i)
        if((off+static_cast<uint64_t>(i)*144)%4096+144>4096) ids.push_back(i);
    for(uint64_t cache: {0ull,64ull}) {
        basalt::ngram::PleReader reader;
        if(!reader.open(argv[2],off,rows,8,cache,err,144)){std::cerr<<err;return 1;}
        std::vector<uint8_t> got(ids.size()*144),want(144);
        std::ifstream file(argv[2],std::ios::binary);
        for(int repeat=0;repeat<2;++repeat) {
            auto ticket=reader.issue(ids.data(),ids.size(),got.data());
            if(!reader.collect(ticket,err)){std::cerr<<err;return 1;}
            for(size_t i=0;i<ids.size();++i) {
                file.seekg(off+static_cast<uint64_t>(ids[i])*144);file.read(reinterpret_cast<char*>(want.data()),144);
                if(!file || std::memcmp(want.data(),got.data()+i*144,144)!=0)return 1;
            }
        }
    }
    std::cout << "PASS direct SSD rows versus independent buffered reads, first/last/mid/page-straddles, cache off/on; ten geometry/fault cases and actual shared Engram header: rows=" << rows
              << " offset=" << off << " bytes=" << actual.file_size() << "\n";
}
