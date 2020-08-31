invalid = false;

tests = ["log.all_csi.6.7.6", "brushteeth_1590158472", "cook_1590161749", "sleeping_post_1597163585", "walk_1590161182"];
scaledTest = false;

for i=1:length(tests)
    test = tests{i};
    
    disp(fprintf("Testing: %s", test));
   
    intelCSIStruct = read_bf_file(sprintf("sample_data/%s.dat", test));
    pythonCSIStruct = load(sprintf("sample_data/%s.mat", test));
   
    for t=1:size(intelCSIStruct)
       intelMat = intelCSIStruct{t};
       if ~isempty(intelMat)
           
           if scaledTest == true
               intelMat = get_scaled_csi(intelMat);
               pythonMat = permute(pythonCSIStruct.csi{t}.scaled_csi, [3 2 1]);
           else
               intelMat = intelMat.csi;
               pythonMat = permute(pythonCSIStruct.csi{t}.csi, [3 2 1]);
           end
           
           %Appears to be some form of rounding error.
           %Direct equality checks fail even though they visually appear
           %identical in MATLAB itself.
           %Instead, we'll use an equality check with a wider tolerance.
           test = abs(intelMat-pythonMat) < 1e4*eps(min(abs(intelMat),abs(pythonMat)));
           
           if all(test(:)==1)
               testNo = testNo+1;
               continue;
           else
               disp(t);
               invalid = true;
           end
       end
    end
end

if invalid == false
    disp("success.");
else
    disp("failure.");
end