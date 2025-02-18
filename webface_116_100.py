import numpy as np
from numpy.linalg import inv, norm, lstsq
from numpy.linalg import matrix_rank as rank
import cv2,random,os
import re

def tformfwd(trans, uv):

    uv = np.hstack((
        uv, np.ones((uv.shape[0], 1))
    ))
    xy = np.dot(uv, trans)
    xy = xy[:, 0:-1]
    return xy


def tforminv(trans, uv):

    Tinv = inv(trans)
    xy = tformfwd(Tinv, uv)
    return xy


def findNonreflectiveSimilarity(uv, xy, options=None):

    options = {'K': 2}

    K = options['K']
    M = xy.shape[0]
    x = xy[:, 0].reshape((-1, 1))  # use reshape to keep a column vector
    y = xy[:, 1].reshape((-1, 1))  # use reshape to keep a column vector
    # print '--->x, y:\n', x, y

    tmp1 = np.hstack((x, y, np.ones((M, 1)), np.zeros((M, 1))))
    tmp2 = np.hstack((y, -x, np.zeros((M, 1)), np.ones((M, 1))))
    X = np.vstack((tmp1, tmp2))
    # print '--->X.shape: ', X.shape
    # print 'X:\n', X

    u = uv[:, 0].reshape((-1, 1))  # use reshape to keep a column vector
    v = uv[:, 1].reshape((-1, 1))  # use reshape to keep a column vector
    U = np.vstack((u, v))
    # print '--->U.shape: ', U.shape
    # print 'U:\n', U

    # We know that X * r = U
    if rank(X) >= 2 * K:
        r, _, _, _ = lstsq(X, U)
        r = np.squeeze(r)
    else:
        raise Exception('cp2tform:twoUniquePointsReq')

    # print '--->r:\n', r

    sc = r[0]
    ss = r[1]
    tx = r[2]
    ty = r[3]

    Tinv = np.array([
        [sc, -ss, 0],
        [ss,  sc, 0],
        [tx,  ty, 1]
    ])

    # print '--->Tinv:\n', Tinv

    T = inv(Tinv)
    # print '--->T:\n', T

    T[:, 2] = np.array([0, 0, 1])

    return T, Tinv


def findSimilarity(uv, xy, options=None):

    options = {'K': 2}

#    uv = np.array(uv)
#    xy = np.array(xy)

    # Solve for trans1
    trans1, trans1_inv = findNonreflectiveSimilarity(uv, xy, options)

    # Solve for trans2

    # manually reflect the xy data across the Y-axis
    xyR = xy
    xyR[:, 0] = -1 * xyR[:, 0]

    trans2r, trans2r_inv = findNonreflectiveSimilarity(uv, xyR, options)

    # manually reflect the tform to undo the reflection done on xyR
    TreflectY = np.array([
        [-1, 0, 0],
        [0, 1, 0],
        [0, 0, 1]
    ])

    trans2 = np.dot(trans2r, TreflectY)

    # Figure out if trans1 or trans2 is better
    xy1 = tformfwd(trans1, uv)
    norm1 = norm(xy1 - xy)

    xy2 = tformfwd(trans2, uv)
    norm2 = norm(xy2 - xy)

    if norm1 <= norm2:
        return trans1, trans1_inv
    else:
        trans2_inv = inv(trans2)
        return trans2, trans2_inv


def get_similarity_transform(src_pts, dst_pts, reflective=True):


    if reflective:
        trans, trans_inv = findSimilarity(src_pts, dst_pts)
    else:
        trans, trans_inv = findNonreflectiveSimilarity(src_pts, dst_pts)

    return trans, trans_inv


def cvt_tform_mat_for_cv2(trans):

    cv2_trans = trans[:, 0:2].T

    return cv2_trans


def get_similarity_transform_for_cv2(src_pts, dst_pts, reflective=True):

    trans, trans_inv = get_similarity_transform(src_pts, dst_pts, reflective)
    cv2_trans = cvt_tform_mat_for_cv2(trans)

    return cv2_trans




def alignment(src_img,src_pts):

    of=125 #(500-250)/2
    image_size=250
    nose_raw=[0.5,0.55]
    eye_off_x=0.1847
    eye_off_y=0.1789
    mouth_off_x=0.1508
    mouth_off_y = 0.1827

    left_eye=[0.5-eye_off_x,0.55-eye_off_y]
    right_eye=[0.5+eye_off_x,0.55-eye_off_y]

    left_mouth=[0.5-mouth_off_x,0.55+mouth_off_y]
    right_mouth = [0.5 + mouth_off_x, 0.55 + mouth_off_y]

    place=[left_eye,right_eye,nose_raw,left_mouth,right_mouth]

    place=np.array(place).astype(np.float32)

    place=place*image_size+of

    s = np.array(src_pts).astype(np.float32)

    tfm = get_similarity_transform_for_cv2(s, place)
    #2 times bigger than raw image
    face_img = cv2.warpAffine(src_img, tfm, (500,500))

    #face_img=cv2.resize(face_img,(300,300),interpolation=cv2.INTER_LINEAR)

    return face_img


'''
img = cv2.imread(filename)
# 0000045/008.jpg	0	95	118	146	101	129	141	113	167	160	153
src_pts = [[95,118],[146,101],[129,141],[113,167],[160,153]]
img = alignment(img,src_pts)

if random.random() > 0.5: img = cv2.flip(img, 1)
if random.random() > 0.5:
    rx = random.randint(0, 2 * 2)
    ry = random.randint(0, 2 * 2)
    img = img[ry:ry + 112, rx:rx + 96, :]
else:
    img = img[2:2 + 112, 2:2 + 96, :]

#img = ( img - 127.5 ) / 128.0

cv2.imwrite('/home/dany/Desktop/MyPicGray.jpg', img)
'''


'''
f = open('/home/dany/Documents/workspace/sphereface_pytorch-master/data/casia_landmark.txt',"r")
lines = f.readlines()#读取全部内容
count=0
for line in lines :

    if count <10:
        count+=1
        line = re.split(r'[\s]', line)
        filename=line[0]
        pts=[]
        for i in range(5):
            pts.append([int(line[2 * i + 2]), int(line[2 * i + 3])])

        #print(filename) 0000045/001.jpg
        #print (pts) [[96, 114], [151, 104], [127, 139], [110, 176], [154, 170]]


#print(count) 454590

'''

def face_aligment(raw_images_dir,aliged_images_dir,landmarks_dir):

    if not os.path.exists(aliged_images_dir):

        os.makedirs(aliged_images_dir)

        for fold in os.listdir(raw_images_dir):

            other_sub_fold = os.path.join(aliged_images_dir, fold)

            os.makedirs(other_sub_fold)

    f = open(landmarks_dir, "r")

    lines = f.readlines()  # 读取全部内容
    count = 0
    for line in lines:

        count += 1
        line = re.split(r'[\s]', line)
        filename = os.path.join(raw_images_dir, line[0])
        aliged_filename=os.path.join(aliged_images_dir, line[0])
        pts = []
        for i in range(5):

            pts.append([int(line[2 * i + 2]), int(line[2 * i + 3])])


        img = cv2.imread(filename)
        img = alignment(img, pts)
        #img = (img - 127.5) / 128.0
        cv2.imwrite(aliged_filename, img,[int(cv2.IMWRITE_JPEG_QUALITY), 100])
        print(count)






face_aligment('/home/dany/Documents/datasets/CASIA-maxpy-clean','/home/dany/Documents/datasets/CASIA-maxpy-clean_warpAffin_500','/home/dany/Downloads/sphereface_pytorch-master/data/casia_landmark.txt')
