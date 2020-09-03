
csi_trace = read_bf_file("sample_data/log.all_csi.6.7.6.dat");

allCSI = zeros(length(csi_trace), 30, 1);

for i=1:length(csi_trace)
    scaled_csi = get_scaled_csi(csi_trace{i});
    csiEntry = permute(scaled_csi, [3 2 1]);
    
    mat = [];
    for j=1:30
        val = db(abs(csiEntry(j,1)));
        mat(j) = val;
    end
    
    allCSI(i,:) = mat;
end

allCSI = rot90(allCSI);
allCSI = flipud(allCSI);

heatmap(allCSI);
colormap jet;