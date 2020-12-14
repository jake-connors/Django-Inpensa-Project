from django.shortcuts import render, redirect
from django.db import models
from django.http import HttpResponse
from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from .forms import SetForm, ModelForm
from .models import dataset, data, model, prediction
from django.db.models import Q
import pandas as pd
from sklearn import preprocessing
import tensorflow as tf
from json import dumps
import numpy as np
from django.views.generic import View
from django.http import JsonResponse, Http404
from sklearn.model_selection import train_test_split
from sklearn.utils import resample
import os
import json.encoder
from django.views.decorators.csrf import csrf_exempt
# Create your views here.

def login(request):
    if request.method == 'POST':
        username = request.POST['uname']
        password = request.POST['psw']

        user = auth.authenticate(username = username, password =password)
        if user is not None:
            auth.login(request, user)
            return redirect('dash')
        
        else:
            messages.info(request,'invalid username or password')
            return redirect('/')
        
    else:
        if request.user.is_authenticated:
            return redirect('dash')
        else:
            return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        first_name = request.POST['fname']
        last_name = request.POST['lname']
        email = request.POST['email']
        user_name = request.POST['uname']
        password1 = request.POST['psw']
        if User.objects.filter(username = user_name).exists():
            messages.info(request,'Username taken')
            return redirect('register')
        elif User.objects.filter(email=email).exists():
            messages.info(request,'Email taken')
            return redirect('register')
        else:
            user = User.objects.create_user(username = user_name, password = password1, email = email, first_name= first_name, last_name = last_name)
            
            user.save()
            messages.info(request,'Account registered successfully')
            return redirect('login')
    else:
        return render(request, 'register.html')

def forgot(request):
    return render(request, 'forgot.html')

def dash(request):
    if request.user.is_authenticated:
        sets = dataset.objects.all().filter(user = request.user).values()
        sets2 =  model.objects.all().filter(user = request.user).values()
        df2 = pd.DataFrame(sets)
        df = pd.DataFrame(sets2)
        df4 = df
        df3 = df2
        if(df3.shape[0]!= 0):
            df3 = df3.fillna(0)
            df3 = df3.sort_values(by=['updated_at'], ascending=False)
            df3['created_at'] = df3['created_at'].astype(str)
            df3['updated_at'] = df3['updated_at'].astype(str)

        sorted_sets = df3.to_dict('records');
        if(df4.shape[0] != 0):
            df4 =df4.fillna(0)
            df4 = df4.sort_values(by=['updated_at'], ascending=False)
            
            df4['created_at'] = df4['created_at'].astype(str)
            df4['updated_at'] = df4['updated_at'].astype(str)

        sorted_models = df4.to_dict('records');
        if(df.shape[0]!= 0):
            df = df[['name', 'accuracy', 'features']]
            if(df.shape[0]>5):
                df= df.head()
            df= df.sort_values(by=['accuracy'], ascending=False)
            model_info = df.to_dict('records')
        else:
            model_info=0
        df2 = pd.DataFrame(sets)
        if(df2.shape[0] != 0):
            df2= df2.sort_values(by=['updated_at'], ascending=False)
            df2 = df2[['name', 'budget', 'approved']]
            df2 =df2.fillna(0)
            df2 = df2.head()
            budget_info = df2.to_dict('records')
        else:
            budget_info=0

        return render(request, 'dashboard.html',{
            'sets': dumps(sorted_sets),
            'sets2': dumps(sorted_models),
            'budget_info':dumps(budget_info),
            'model_info':dumps(model_info)
        })
    else:
        return redirect('login')

def logout(request):
    auth.logout(request)
    messages.info(request,'You have successfully logged out')
    return redirect('/')

'''
def upload(request):
    context = {}
    if request.method =='POST':
        uploaded_file = request.FILES['document']
        fs = FileSystemStorage()
        name = fs.save(uploaded_file.name, uploaded_file)
        context['url'] = fs.url(name)
    return render(request, 'upload.html', context)


'''



##upload page that lets the user upload a new file



def upload_db(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            f = request.FILES['Project Data'].temporary_file_path()
            try:
                df = pd.read_excel(f)
            except Exception:
                df = pd.read_csv(f)
            df = df.fillna(0)
            df = df.reset_index().groupby("ID", as_index=False).max()
            df['accepted'] = 0
            df['TCO'] = df['CapEx'] + df['OneTime'] + df['OnGoing']
            df['TVO'] = df['Revenue'] +df['Saving']+df['Avoid']
            df['NET'] = df['TVO'] - df['TCO']
            df['ROI'] = (df['NET']/df['TCO'])*100
            instance = dataset(user = request.user, name = request.POST['name'], budget = request.POST['budget'])
            instance.save()
            df_records = df.to_dict('records')
            
            model_instances = [data(
                name =record['ID'],
                TCO =record['TCO'],
                TVO =record['TVO'],
                NET =record['NET'],
                PP =record['PP'],
                ROI =record['ROI'],
                CapEx =record['CapEx'],
                OneTime =record['OneTime'],
                OnGoing =record['OnGoing'],
                Revenue =record['Revenue'],
                Saving =record['Saving'],
                Avoid =record['Avoid'],
                CostGrade =record['Cost Grade'],
                ValueScore =record['Value Score'],
                RiskScore =record['Risk Score'],
                BlendedScore =record['Blended Score'],
                CalcPriority =record['Calc Priority'],
                OverridedPriority =record['Overrided Priority'],
                dsid = instance,
                accepted = record['accepted']
                
            ) for record in df_records]
            data.objects.bulk_create(model_instances)

            count = data.objects.filter(dsid = instance).count()
            if (count != 0):
                instance.size = count
                instance.save()
            else:
                instance.delete()


            
            return redirect('dash')
                

        else:
            form = SetForm()
            return render(request, 'upload_db.html',{'form': form})
    else:
        return redirect('login')


def test(request):
    dsid = request.GET['dsid']
    return render(request, 'test.html',{
        'dsid': dsid,
        'predict':0
    })



##shows the list of files uploaded by that user

def set_list(request):
    if request.user.is_authenticated:
        sets = dataset.objects.all().filter(user = request.user).values()
        return render(request, 'set_list.html',{
            'sets': sets
        })
    else:
        return redirect('login')

def view(request):
    if request.user.is_authenticated:
        if request.method=="POST":



            return render(request, 'view_dataset.html')
        else:
            
            return render(request, 'view_dataset.html',{
                'dataset' : request.GET['datasetid'],
                'predict':0

            })
    else:
        return redirect('login')


def predict(request):
    if request.user.is_authenticated:
        if request.method == "GET":
            modelid = request.GET['model']
            dsetid = request.GET['dataset']
            datapoints = data.objects.all().filter(dsid = dsetid).values()
            exists = False
            old = False
            dataset_instance = dataset.objects.get(id = dsetid)
            if(prediction.objects.filter(mid = modelid, did = datapoints[0]['id']).exists()):
                exists = True
                pred_instance =prediction.objects.get(mid = modelid, did = datapoints[0]['id'])
                if  dataset_instance.updated_at > pred_instance.created_at:
                    old = True
            
            if (exists == False or old == True):
                if(old):
                    prediction.objects.filter(mid = modelid ,dsid = dsetid).delete()
                model1 = model.objects.get(id = modelid)
                settings = {'TCO' : model1.TCO,
                'TVO': model1.TVO,
                'NET' : model1.NET,
                'PP' : model1.PP,
                'ROI' : model1.ROI,
                'CapEx' : model1.CapEx,
                'OneTime' : model1.OneTime,
                'OnGoing' : model1.OnGoing,
                'Revenue' : model1.Revenue,
                'Saving' : model1.Saving,
                'Avoid' : model1.Avoid,
                'CostGrade' : model1.CostGrade,
                'ValueScore' : model1.ValueScore,
                'RiskScore' : model1.RiskScore,
                'BlendedScore' : model1.BlendedScore,
                'CalcPriority': model1.CalcPriority,
                'OverridedPriority' : model1.OverridedPriority
                }

                df = pd.DataFrame(datapoints)
                df1 = df.drop(df.columns[[0, 1, 2, 20]], axis = 1)
                for x in settings:
                    if settings[x] == 0:
                        df1 = df1.drop(x, axis = 1)
                df1 = df1.fillna(0)
                x = df1.values #returns a numpy array
                min_max_scaler = preprocessing.MinMaxScaler()
                x_scaled = min_max_scaler.fit_transform(x)
                loadedmodel = tf.keras.models.load_model(model1.kfile)
                pred = loadedmodel.predict(x_scaled)
                
                df['pred'] = pred
                df_records = df.to_dict('records')
                model_instances = [prediction(
                    did =data.objects.get(id = record['id']),
                    mid =model1,
                    score = record['pred'],
                    dsid = dataset.objects.get(id = dsetid)

                        
                ) for record in df_records]
                prediction.objects.bulk_create(model_instances)

            df = pd.DataFrame(datapoints)

            df2 =  pd.DataFrame(prediction.objects.all().filter(mid = modelid, dsid = dsetid).values())
            df['score'] = df2['score']
            df = df.fillna(0)
            df['CalcPriority'] = ['Low' if x== 1.0 else 'Medium' if x == 2.0 else 'High' if x==3.0 else 'Critical' for x in df['CalcPriority']]
            df['OverridedPriority'] = ['Low' if x== 1 else 'Medium' if x == 2 else 'High' if x==3 else 'Critical' for x in df['OverridedPriority']]

            df = df.sort_values(by = ['accepted','score'], ascending = False)
            df_records1 = df.to_dict('records')
            return render(request, 'view_dataset.html',{
                'sets':dumps(df_records1),
                'mid':modelid,
                'dataset' : dsetid,
                'predict':1

            })
        else:
            sets = dataset.objects.all().filter(user = request.user).values()
            return render(request, 'set_list.html',{
            'sets': sets
            })
    else:
        return redirect('login')



def cmodel(request):
    if request.user.is_authenticated:
        if request.method =="POST":
            data = pd.read_excel("static/data/fixed_data.xlsx")
            settings = {'TCO' : request.POST['TCO'],
            'TVO': request.POST['TVO'],
            'NET' : request.POST['NET'],
            'PP' : request.POST['PP'],
            'ROI' : request.POST['ROI'],
            'CapEx' : request.POST['CapEx'],
            'OneTime' : request.POST['OneTime'],
            'OnGoing' : request.POST['OnGoing'],
            'Revenue' : request.POST['Revenue'],
            'Saving' : request.POST['Saving'],
            'Avoid' : request.POST['Avoid'],
            'Cost Grade' : request.POST['CostGrade'],
            'Value Score' : request.POST['ValueScore'],
            'Risk Score' : request.POST['RiskScore'],
            'Blended Score' : request.POST['BlendedScore'],
            'Calc Priority': request.POST['CalcPriority']
            }
            data = data.fillna(0)
            features = 17
            testprint = []
            for x in settings:
                if settings[x] == '0':
                    features -= 1
                    data = data.drop(x, axis = 1)
                elif settings[x] =='1':
                    testprint.append(-0.5)
                elif settings[x] =='2':
                    testprint.append(0.0)
                elif settings[x] =='3':
                    testprint.append(0.5)

            testprint.append(0)
            new_bias = np.array(testprint)
            data = data.drop(data.columns[0], axis=1)
            x = data.values #returns a numpy array
            min_max_scaler = preprocessing.MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(x)
            data = pd.DataFrame(x_scaled)
            train=data.sample(frac=0.8) #random state is a seed value
            test=data.drop(train.index)
            dist = train.groupby([train.shape[1]-1]).agg({0:'count'})
            dist_0 = dist[0][0]
            dist_1 = dist[0][1]
            train_1 = train.loc[train[train.shape[1]-1]==1]
            train_0 = train.loc[train[train.shape[1]-1]==0]
            train_1_new = resample(train_1, replace=True, n_samples=dist_0, random_state=1) 
            newdf = pd.DataFrame(train_1_new)
            frames = [train_0, newdf]
            new_train = pd.concat(frames)
            new_train.groupby([train.shape[1]-1]).agg({0:'count'})
            X_train = new_train.drop(new_train[[train.shape[1]-1]], axis=1)
            Y_train = new_train[[train.shape[1]-1]]
            X_test = test.drop(test[[test.shape[1]-1]], axis = 1)
            Y_test = test[test.shape[1]-1]

            weights = np.zeros((test.shape[1]-1, test.shape[1]-1))

            model1 = tf.keras.Sequential([
                tf.keras.Input(shape=(data.shape[1]-1)),
                tf.keras.layers.Dense(data.shape[1]-1, activation="relu"),
                tf.keras.layers.Dense(1, activation="sigmoid"),
                
            ])
            weights = model1.layers[0].get_weights()[0]
            model1.layers[0].set_weights([weights,new_bias])

            model1.compile(optimizer='adam',
                        loss='binary_crossentropy',
                        metrics=['accuracy'])

            history = model1.fit(X_train,
                                Y_train,
                                epochs =100,
                                validation_data= (X_test,Y_test),
                                verbose=0,
                            shuffle = False,
                            batch_size =64)

            acc = history.history['accuracy']
            val_acc = history.history.get('val_accuracy')[-1]
            import random
            model_location = "static/data/saved_models/"+str(request.user.username)+"_"+str(request.POST['modname'])+"_"+str(random.randrange(100,999,3))+".h5"
            model_location = model_location.replace(" ", "")
            model1.save(model_location)
            instance = model(user = request.user,
                name = request.POST['modname'],
                details = request.POST['description'],
                kfile = model_location,
                features = features,
                TCO = settings['TCO'], 
                TVO = settings['TVO'],
                NET= settings['NET'],
                PP = settings['PP'],
                ROI = settings['ROI'],
                CapEx = settings['CapEx'],
                OneTime= settings['OneTime'],
                OnGoing = settings['OnGoing'],
                Revenue = settings['Revenue'],
                Saving = settings['Saving'],
                Avoid = settings['Avoid'],
                CostGrade = settings['Cost Grade'],
                ValueScore = settings['Value Score'],
                RiskScore = settings['Risk Score'],
                BlendedScore = settings['Blended Score'],
                CalcPriority = settings['Calc Priority'],
                OverridedPriority = 2) 
            
            instance.accuracy = val_acc*100
            instance.save()

        return redirect('/dash')
    else:
        return redirect('login')

def delete_dataset(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            dsid = request.POST['dsid']
            dataset.objects.filter(id = dsid).delete()

        return redirect('dash')
    else:
        return redirect('login')

def delete_data(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            dsid = request.POST['dsid']
            dataid = request.POST['dataid']
            data.objects.filter(id = dataid).delete()
            instance = dataset.objects.get(id = dsid)
            count = data.objects.filter(dsid = instance).count()
            instance.size = count
            instance.save()
            sets = data.objects.all().filter(dsid = dsid).values()
            df = pd.DataFrame(sets)
            df = df.fillna("")
            sets = df.to_dict('records')
            return render(request, 'edit.html',{
                'sets':sets,
                'dataset' : dsid

            })
        return redirect('dash')
    else:
        return redirect('login')

def delete_model(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            mid = request.POST['model']
            instance = model.objects.get(id = mid)
            os.remove(instance.kfile)
            instance.delete()
        return redirect('dash')
    else:
        return redirect('login')

def edit(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            redirect('dash')
        else:
            did = request.GET['dsid']
            dataset1 = dataset.objects.get(id = did)
            sets = data.objects.all().filter(dsid = did).values()
            df = pd.DataFrame(sets)
            df = df.fillna("")
            sets = df.to_dict('records')
            sets = dumps(sets)
            return render(request, 'edit.html',{
                'sets':sets,
                'dataset' : did,
                'setname': dataset1.name

            })
    else:
        return redirect('login')

def dataList(request):
    sets = dataset.objects.all().filter(user = request.user).values()
    df = pd.DataFrame(sets)
    if(df.shape[0] != 0):
        df = df[['id', 'name']]
    sets = df.to_dict('records')
    sets = dumps(sets)
    return JsonResponse(sets, safe=False)




@csrf_exempt
def edit_single_data(request):
    if request.user.is_authenticated:
        dataid = request.POST.get('row_id')
        datacolumn = request.POST.get('col_name')
        datavalue = request.POST.get('col_val')
        if (datavalue == ""):
            datavalue = None
        instance = data.objects.get(id = dataid)

        
        if(datacolumn == "name"):
            instance.name = datavalue
        elif(datacolumn == "TCO"):
            instance.TCO = float(datavalue)
        elif(datacolumn == "TVO"):
            instance.TVO = float(datavalue)
        elif(datacolumn == "NET"):
            instance.NET = float(datavalue)
        elif(datacolumn == "PP"):
            instance.PP = float(datavalue)
        elif(datacolumn == "ROI"):
            instance.ROI = float(datavalue)
        elif(datacolumn == "CapEx"):
            instance.CapEx = float(datavalue)
        elif(datacolumn == "OneTime"):
            instance.OneTime = float(datavalue)
        elif(datacolumn == "OnGoing"):
            instance.OnGoing = float(datavalue)
        elif(datacolumn == "Revenue"):
            instance.Revenue = float(datavalue)
        elif(datacolumn == "Saving"):
            instance.Saving = float(datavalue)
        elif(datacolumn == "Avoid"):
            instance.Avoid = float(datavalue)
        elif(datacolumn == "CostGrade"):
            instance.CostGrade = float(datavalue)
        elif(datacolumn == "ValueScore"):
            instance.ValueScore = float(datavalue)
        elif(datacolumn == "RiskScore"):
            instance.RiskScore = float(datavalue)
        elif(datacolumn == "BlendedScore"):
            instance.BlendedScore = float(datavalue)
        elif(datacolumn == "CalcPriority"):
            instance.CalcPriority = float(datavalue)
        elif(datacolumn == "OverridedPriority"):
            instance.OverridedPriority = int(datavalue)
        
        instance.TCO = (instance.CapEx+ instance.OneTime+instance.OnGoing) 
        instance.TVO = (instance.Revenue +instance.Saving+instance.Avoid)
        instance.NET = (instance.TVO - instance.TCO)
        try:
            instance.ROI = (float(instance.NET)/float(instance.TCO))*100
        except Exception:
            instance.ROI = instance.ROI
        
        instance.save()
        dsid = instance.dsid
        instance2 = dataset.objects.get(id = dsid.id)
        instance2.save()


        return JsonResponse({'status': True}, status = 200)
    else:
        raise Http404


@csrf_exempt
def edit_whole_data(request):
    if request.user.is_authenticated:
        instance = data.objects.get(id = request.POST.get('row_id'))
        instance.name = request.POST.get('name')
        instance.TCO = (float(request.POST.get('CapEx')) + float(request.POST.get('OneTime')) +float(request.POST.get('OnGoing'))) 
        instance.TVO = (float(request.POST.get('Revenue')) +float(request.POST.get('Saving')) +float(request.POST.get('Avoid')))
        instance.NET = (instance.TVO - instance.TCO)
        instance.PP = float(request.POST.get('PP'))
        try:
            instance.ROI = (instance.NET/float(instance.TCO))*100
        except Exception:
            instance.ROI = float(request.POST['ROI'])
        instance.CapEx = float(request.POST.get('CapEx'))
        instance.OneTime = float(request.POST.get('OneTime'))
        instance.OnGoing = float(request.POST.get('OnGoing'))
        instance.Revenue = float(request.POST.get('Revenue'))
        instance.Saving = float(request.POST.get('Saving'))
        instance.Avoid = float(request.POST.get('Avoid'))
        instance.CostGrade = float(request.POST.get('CostGrade'))
        instance.ValueScore = float(request.POST.get('ValueScore'))
        instance.RiskScore = float(request.POST.get('RiskScore'))
        instance.BlendedScore = float(request.POST.get('BlendedScore'))
        instance.CalcPriority = float(request.POST.get('CalcPriority'))
        instance.OverridedPriority = int(request.POST.get('OverridedPriority'))
        
        instance.save()
        dsid = instance.dsid
        instance2 = dataset.objects.get(id = dsid.id)
        instance2.save()

        
        return JsonResponse({'status': True}, status = 200)
    else:
        raise Http404
@csrf_exempt
def delete_row(request):
    if request.method =='POST':
        did = request.POST['row_id']
        instance = data.objects.get(id = did)
        if(instance.delete()):
            dataset1 = dataset.objects.get(id = request.POST['dsid'])
            dataset1.save()
            return JsonResponse({'status':'success'}, safe=False)
        else:
            return JsonResponse({'status':'error'}, safe=False)
    else:
        raise Http404
        
def get_data(request):
    if request.user.is_authenticated:
        if request.method =='GET':
            dsid = request.GET['dsid']
            daata = data.objects.filter(dsid = dsid).values()
            df = pd.DataFrame(daata)
            df = df.fillna(0)
            sets = df.to_dict('records')
            sets = dumps(sets)
            return JsonResponse(sets, safe=False)
        else:
            raise Http404
    else:
        raise Http404



def get_table_data(request):
    if request.user.is_authenticated:
        if request.method == 'GET':
            dsid = request.GET['dsid']
            stuff = data.objects.filter(dsid = dsid).values()
            df = pd.DataFrame(stuff)
            df = df.fillna(0)
            df['CalcPriority'] = ['Low' if x== 1.0 else 'Medium' if x == 2.0 else 'High' if x==3.0 else 'Critical' for x in df['CalcPriority']]
            df['OverridedPriority'] = ['Low' if x== 1 else 'Medium' if x == 2 else 'High' if x==3 else 'Critical' for x in df['OverridedPriority']]
            df = df.sort_values(by =['accepted'], ascending=False)
            sets = df.to_dict('records')
            sets = dumps(sets)
            return JsonResponse(sets, safe=False)
        else:
            raise Http404
    else:
        raise Http404



def get_data_details(request):
    if request.user.is_authenticated:
        if request.method =="GET":
            dsid = request.GET['dsid']
            stuff = dataset.objects.filter(id = dsid).values()
            stuff = list(stuff)
            return JsonResponse(stuff, safe=False)
        else:
            raise Http404
    else:
        raise Http404


def get_models(request):
    if request.user.is_authenticated:
        if request.method =="GET":
            stuff = model.objects.filter(Q(user = request.user) | Q(user= 1)).values()
            stuff = list(stuff)
            return JsonResponse(stuff, safe=False)
        else:
            raise Http404
    else: 
        raise Http404




@csrf_exempt
def add_row(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            dataset1 = dataset.objects.get(id = request.POST['dsid'])
            instance = data(dsid = dataset1, name= request.POST['name'],TVO= float(request.POST['tvo']),TCO= float(request.POST['tco']),NET= float(request.POST['net']),PP= float(request.POST['pp']),ROI= float(request.POST['roi']),CapEx= float(request.POST['capex']),OneTime= float(request.POST['onetime']),OnGoing= float(request.POST['ongoing']),Revenue= float(request.POST['revenue']),Saving= float(request.POST['saving']),Avoid= float(request.POST['avoid']),CostGrade= float(request.POST['costgrade']),ValueScore= float(request.POST['valuescore']),RiskScore= float(request.POST['riskscore']),BlendedScore= float(request.POST['blendedscore']),CalcPriority= float(request.POST['calcpriority']),OverridedPriority= int(request.POST['overridedpriority']),accepted=0)
            instance.TCO = (instance.CapEx+ instance.OneTime+instance.OnGoing) 
            instance.TVO = (instance.Revenue +instance.Saving+instance.Avoid)
            instance.NET = (instance.TVO - instance.TCO)
            try:
                instance.ROI = (instance.NET/float(instance.TCO))*100
            except Exception:
                instance.ROI = float(request.POST['roi'])
            
            
            
            instance.save()
            dataset1.save()
            test= instance.id
            if(test != None):
                return JsonResponse({'status':'success'}, safe=False)
            else:
                return JsonResponse({'status':'error'}, safe=False)
        else:
            raise Http404
    else:
        raise Http404

@csrf_exempt
def edit_budget(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            datasetid = request.POST['datasetid']
            new_budget= request.POST['new_budget']
            instance = dataset.objects.get(id = datasetid)
            instance.budget = new_budget
            instance.save()
            if (instance.budget == new_budget):
                return JsonResponse({'status':'success'}, safe=False)
            else:
                return JsonResponse({'status':'error'}, safe=False)
        else:
            raise Http404
    else:
        raise Http404

@csrf_exempt
def approve(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            idlist = request.POST['list'].split(',')
            for x in idlist:
                if x =="":
                    break
                else:
                    instance = data.objects.get(id = x)
                    instance.accepted = 1
                    instance.save()
            datasetid = instance.dsid.id
            raw_data = data.objects.filter(dsid = datasetid).values()
            dinstance = dataset.objects.get(id = datasetid)
            df = pd.DataFrame(raw_data)
            df = df.loc[df['accepted']==1]
            total_approved = df['TCO'].agg('sum')
            dinstance.approved = total_approved
            dinstance.save()
            return JsonResponse({'status':'success'}, safe=False)
        else:
            raise Http404
    else:
        raise Http404

@csrf_exempt
def unapprove(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            idlist = request.POST['unlist'].split(',')
            idlist.pop()
            for x in idlist:
                instance = data.objects.get(id = x)
                instance.accepted = 0
                instance.save()
            datasetid = instance.dsid.id
            raw_data = data.objects.filter(dsid = datasetid).values()
            dinstance = dataset.objects.get(id = datasetid)
            df = pd.DataFrame(raw_data)
            df = df.loc[df['accepted']==1]
            total_approved = df['TCO'].agg('sum')
            dinstance.approved = total_approved
            dinstance.save()
            return JsonResponse({'status':'success'}, safe=False)
        else:
            raise Http404
    else:
        raise Http404

@csrf_exempt
def new_name(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            datasetid = request.POST['datasetid']
            new_name= request.POST['new_name']
            instance = dataset.objects.get(id = datasetid)
            instance.name = new_name
            instance.save()
            if (instance.name == new_name):
                return JsonResponse({'status':'success'}, safe=False)
            else:
                return JsonResponse({'status':'error'}, safe=False)
        else:
            raise Http404
    else:
        raise Http404
@csrf_exempt
def get_pred(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            datasetid = request.POST['dsid']
            modelid= request.POST['modelid']
            datapoints = data.objects.filter(dsid = datasetid).values()
            preds = prediction.objects.filter(dsid = datasetid, mid = modelid).values()
            df = pd.DataFrame(datapoints)
            df1 = pd.DataFrame(preds)
            df['score'] = df1['score']
            df = df.fillna(0)
            df['CalcPriority'] = ['Low' if x== 1.0 else 'Medium' if x == 2.0 else 'High' if x==3.0 else 'Critical' for x in df['CalcPriority']]
            df['OverridedPriority'] = ['Low' if x== 1 else 'Medium' if x == 2 else 'High' if x==3 else 'Critical' for x in df['OverridedPriority']]

            df = df.sort_values(by = ['accepted','score'], ascending = False)
            df_records1 = df.to_dict('records')
            
            

            return JsonResponse(dumps(df_records1), safe=False)
        else:
            raise Http404
    else:
        raise Http404